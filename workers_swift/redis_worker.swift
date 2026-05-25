import Foundation
import Vision
import AppKit

// --- Configuration ---
let REDIS_QUEUE = "ocr_tasks"
let SQLITE_DB_PATH = "../database/registrations.db" // Relative to script or absolute
let OLLAMA_HOST = ProcessInfo.processInfo.environment["OLLAMA_HOST"] ?? "http://localhost:11434"
let OLLAMA_MODEL = ProcessInfo.processInfo.environment["OLLAMA_MODEL"] ?? "bcard-lora"

// Helper to print to stderr
func debugPrint(_ message: String) {
    if let data = (message + "\n").data(using: .utf8) {
        FileHandle.standardError.write(data)
    }
}

func _stringValue(_ value: Any?) -> String {
    guard let value else { return "" }
    if value is NSNull { return "" }
    if let string = value as? String {
        return string.trimmingCharacters(in: .whitespacesAndNewlines)
    }
    if JSONSerialization.isValidJSONObject(["value": value]),
       let encoded = try? JSONSerialization.data(withJSONObject: value, options: []),
       let stringValue = String(data: encoded, encoding: .utf8) {
        return stringValue
    }
    return "\(value)".trimmingCharacters(in: .whitespacesAndNewlines)
}

func normalizePhone(_ value: Any?) -> String {
    let phone = _stringValue(value)
    guard !phone.isEmpty else { return "" }

    let replaced = phone
        .replacingOccurrences(of: "-", with: " ")
        .replacingOccurrences(of: ".", with: " ")
        .replacingOccurrences(of: "+", with: " ")
        .replacingOccurrences(of: "(", with: " ")
        .replacingOccurrences(of: ")", with: " ")

    return replaced.replacingOccurrences(
        of: "\\s+",
        with: " ",
        options: .regularExpression
    )
    .trimmingCharacters(in: .whitespacesAndNewlines)
}

func normalizeExtractedFields(_ raw: [String: Any], rawOCR: String? = nil) -> [String: String] {
    return [
        "full_name": _stringValue(raw["full_name"] ?? raw["name"]),
        "title": _stringValue(raw["title"] ?? raw["job_title"] ?? raw["position"] ?? raw["role"]),
        "email": _stringValue(raw["email"]),
        "company": _stringValue(raw["company"] ?? raw["org"]),
        "phone": normalizePhone(raw["phone"] ?? raw["tel"]),
        "address": _stringValue(raw["address"]),
        "raw_ocr": rawOCR ?? "",
    ]
}

// Helper to run shell commands
func runCommand(_ args: [String]) -> String? {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
    process.arguments = args
    
    let outputPipe = Pipe()
    process.standardOutput = outputPipe
    
    try? process.run()
    process.waitUntilExit()
    
    let data = outputPipe.fileHandleForReading.readDataToEndOfFile()
    return String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines)
}


func processTask(task: [String: Any]) {
    guard let taskId = task["task_id"] as? String,
          let regId = task["reg_id"] as? String,
          let imagePath = task["image_path"] as? String else {
        debugPrint("Invalid task format")
        return
    }
    
    debugPrint("Processing task: \(taskId) for \(regId)")
    
    let imageUrl = URL(fileURLWithPath: imagePath)
    guard let image = NSImage(contentsOf: imageUrl),
          let tiffData = image.tiffRepresentation,
          let cgImage = NSBitmapImageRep(data: tiffData)?.cgImage else {
        updateStatus(taskId: taskId, status: "error", error: "Failed to load image")
        return
    }

    let requestHandler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    request.recognitionLanguages = ["ja-JP", "en-US"]

    do {
        try requestHandler.perform([request])
        guard let observations = request.results else {
            updateStatus(taskId: taskId, status: "error", error: "No text recognized")
            return
        }
        
        let recognizedStrings = observations.compactMap { $0.topCandidates(1).first?.string }
        let ocrText = recognizedStrings.joined(separator: "\n")
        
        if ocrText.isEmpty {
            updateStatus(taskId: taskId, status: "error", error: "No text recognized")
            return
        }

        // Call Ollama
        callOllama(taskId: taskId, regId: regId, ocrText: ocrText)

    } catch {
        updateStatus(taskId: taskId, status: "error", error: error.localizedDescription)
    }
}

func callOllama(taskId: String, regId: String, ocrText: String) {
    let prompt = """
    Extract business card information from the OCR text.

    Return EXACTLY one JSON object with EXACTLY these 6 keys:
    {
      "full_name": "",
      "title": "",
      "email": "",
      "company": "",
      "phone": "",
      "address": ""
    }

    Rules:
    1. Do not output any extra keys.
    2. Use empty string "" for missing fields.
    3. `full_name` is the person's name.
    4. `title` is the job title or role.
    5. `email` must contain only the email address.
    6. `company` is the organization name.
    7. `phone` is the main phone or mobile contact.
    8. `address` is the physical address.
    9. Reconstruct broken OCR text logically, but do not invent facts.
    10. Output JSON only, with no markdown and no explanation.

    OCR Text:
    \(ocrText)

    JSON Result:
    """

    debugPrint("Using Ollama model: \(OLLAMA_MODEL)")
    let ollamaUrl = URL(string: "\(OLLAMA_HOST)/api/generate")!
    var urlRequest = URLRequest(url: ollamaUrl)
    urlRequest.httpMethod = "POST"
    urlRequest.addValue("application/json", forHTTPHeaderField: "Content-Type")

    let body: [String: Any] = [
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": false
    ]

    urlRequest.httpBody = try? JSONSerialization.data(withJSONObject: body)

    let semaphore = DispatchSemaphore(value: 0)
    let task = URLSession.shared.dataTask(with: urlRequest) { data, response, error in
        defer { semaphore.signal() }
        
        if let error = error {
            finishTask(taskId: taskId, regId: regId, ocrText: ocrText, fields: [:], error: "Ollama failed: \(error.localizedDescription)")
            return
        }

        guard let data = data,
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let extraction = json["response"] as? String else {
            finishTask(taskId: taskId, regId: regId, ocrText: ocrText, fields: [:], error: "Failed to parse Ollama response structure")
            return
        }

        debugPrint("--- Ollama Raw Response ---\n\(extraction)\n--- End ---")

        // Clean and parse extraction (find the first { and the last })
        var jsonRange: String = extraction
        if let start = extraction.firstIndex(of: "{"),
           let end = extraction.lastIndex(of: "}") {
            jsonRange = String(extraction[start...end])
        }
        
        let resultStr = jsonRange.trimmingCharacters(in: .whitespacesAndNewlines)
        if let resultData = resultStr.data(using: .utf8),
           let fields = try? JSONSerialization.jsonObject(with: resultData) as? [String: Any] {
            finishTask(taskId: taskId, regId: regId, ocrText: ocrText, fields: normalizeExtractedFields(fields, rawOCR: ocrText), error: nil)
        } else {
            finishTask(taskId: taskId, regId: regId, ocrText: ocrText, fields: [:], error: "LLM output was not valid JSON: \(resultStr)")
        }
    }

    task.resume()
    semaphore.wait()
}

func finishTask(taskId: String, regId: String, ocrText: String, fields: [String: String], error: String?) {
    if let error = error {
        debugPrint("Task \(taskId) failed: \(error)")
        updateStatus(taskId: taskId, status: "error", error: error)
        return
    }
    
    // 1. Update SQLite
    updateDatabase(regId: regId, ocrText: ocrText, fields: fields)
    
    // 2. Update Redis Status
    updateStatus(taskId: taskId, status: "done", text: ocrText, fields: fields)
    
    debugPrint("Task \(taskId) completed successfully")
}

func updateDatabase(regId: String, ocrText: String, fields: [String: String]) {
    let dbPath = URL(fileURLWithPath: #file).deletingLastPathComponent().appendingPathComponent(SQLITE_DB_PATH).path

    let fullName = (fields["name"] ?? fields["full_name"] ?? "").replacingOccurrences(of: "'", with: "''")
    let email = (fields["email"] ?? "").replacingOccurrences(of: "'", with: "''")
    let phone = (fields["phone"] ?? "").replacingOccurrences(of: "'", with: "''")
    let title = (fields["title"] ?? "").replacingOccurrences(of: "'", with: "''")
    let company = (fields["company"] ?? "").replacingOccurrences(of: "'", with: "''")
    let address = (fields["address"] ?? "").replacingOccurrences(of: "'", with: "''")
    let escapedOCR = ocrText.replacingOccurrences(of: "'", with: "''")
    let escapedRegId = regId.replacingOccurrences(of: "'", with: "''")

    let sql = """
    INSERT INTO registrations (
        registration_id, full_name, email, phone, title, company, address, last_bcard_text, created_at
    ) VALUES (
        '\(escapedRegId)', '\(fullName)', '\(email)', '\(phone)', '\(title)', '\(company)', '\(address)', '\(escapedOCR)',
        datetime('now', 'localtime')
    )
    ON CONFLICT(registration_id) DO UPDATE SET
        full_name = CASE WHEN excluded.full_name <> '' THEN excluded.full_name ELSE registrations.full_name END,
        email = CASE WHEN excluded.email <> '' THEN excluded.email ELSE registrations.email END,
        phone = CASE WHEN excluded.phone <> '' THEN excluded.phone ELSE registrations.phone END,
        title = CASE WHEN excluded.title <> '' THEN excluded.title ELSE registrations.title END,
        company = CASE WHEN excluded.company <> '' THEN excluded.company ELSE registrations.company END,
        address = CASE WHEN excluded.address <> '' THEN excluded.address ELSE registrations.address END,
        last_bcard_text = CASE WHEN excluded.last_bcard_text <> '' THEN excluded.last_bcard_text ELSE registrations.last_bcard_text END,
        created_at = datetime('now', 'localtime');
    """

    for attempt in 1...5 {
        if runCommand(["sqlite3", dbPath, sql]) != nil {
            return
        }
        Thread.sleep(forTimeInterval: 0.5 * Double(attempt))
    }
    debugPrint("Failed to update SQLite for \(regId)")
}

func updateStatus(taskId: String, status: String, text: String = "", fields: [String: Any] = [:], error: String? = nil) {
    let now = Date().timeIntervalSince1970
    var statusDict: [String: Any] = [
        "status": status,
        "text": text,
        "fields": fields,
        "updated_at": now
    ]
    if let error = error {
        statusDict["error"] = error
    }
    
    if let data = try? JSONSerialization.data(withJSONObject: statusDict, options: []),
       let jsonStr = String(data: data, encoding: .utf8) {
        _ = runCommand(["redis-cli", "setex", "ocr_status:\(taskId)", "3600", jsonStr])
    }
}

// --- Main Loop ---
debugPrint("Swift Redis Worker started. Listening on \(REDIS_QUEUE)...")

while true {
    // BLPOP returns: 1) list name, 2) value
    if let output = runCommand(["redis-cli", "BLPOP", REDIS_QUEUE, "0"]) {
        // Output might be "ocr_tasks\n{...}"
        let lines = output.components(separatedBy: .newlines)
        if lines.count >= 2 {
            let jsonStr = lines[1]
            if let data = jsonStr.data(using: .utf8),
               let taskDict = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                processTask(task: taskDict)
            }
        }
    }
    Thread.sleep(forTimeInterval: 0.1)
}
