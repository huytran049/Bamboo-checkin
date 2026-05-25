import Foundation
import Vision
import AppKit

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

func normalizeExtractedFields(_ raw: [String: Any], rawOCR: String? = nil) -> [String: Any] {
    var normalized: [String: Any] = [
        "full_name": _stringValue(raw["full_name"] ?? raw["name"]),
        "title": _stringValue(raw["title"] ?? raw["job_title"] ?? raw["position"] ?? raw["role"]),
        "email": _stringValue(raw["email"]),
        "company": _stringValue(raw["company"] ?? raw["org"]),
        "phone": normalizePhone(raw["phone"] ?? raw["tel"]),
        "address": _stringValue(raw["address"]),
    ]
    if let rawOCR {
        normalized["raw_ocr"] = rawOCR
    }
    return normalized
}

let OLLAMA_HOST = ProcessInfo.processInfo.environment["OLLAMA_HOST"] ?? "http://localhost:11434"
let OLLAMA_MODEL = ProcessInfo.processInfo.environment["OLLAMA_MODEL"] ?? "business-card"


guard CommandLine.arguments.count > 1 else {
    print("{\"error\": \"Usage: swift ocr_worker.swift <image_path>\"}")
    exit(1)
}

let imagePath = CommandLine.arguments[1]
let imageUrl = URL(fileURLWithPath: imagePath)

// Check if file exists
if !FileManager.default.fileExists(atPath: imagePath) {
    print("{\"error\": \"File not found: \(imagePath)\"}")
    exit(1)
}

// 2. Perform OCR using Vision
guard let image = NSImage(contentsOf: imageUrl),
      let tiffData = image.tiffRepresentation,
      let cgImage = NSBitmapImageRep(data: tiffData)?.cgImage else {
    print("{\"error\": \"Failed to load image\"}")
    exit(1)
}

let requestHandler = VNImageRequestHandler(cgImage: cgImage, options: [:])
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
request.recognitionLanguages = ["ja-JP", "en-US"]

do {
    try requestHandler.perform([request])
    guard let observations = request.results else {
        print("{\"error\": \"No text recognized\"}")
        exit(1)
    }
    
    let recognizedStrings = observations.compactMap { $0.topCandidates(1).first?.string }
    let ocrText = recognizedStrings.joined(separator: "\n")
    
    if ocrText.isEmpty {
        print("{\"error\": \"No text recognized\"}")
        exit(1)
    }

    debugPrint("--- OCR Text Start ---")
    debugPrint(ocrText)
    debugPrint("--- OCR Text End ---")

    // 3. Call Ollama for extraction
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
        if let error = error {
            // If Ollama fails, we return the raw OCR text as a fallback
            let fallback: [String: Any] = [
                "error": "Ollama call failed: \(error.localizedDescription)",
                "raw_ocr": ocrText,
                "name": "", "title": "", "company": "", "email": "", "phone": "", "address": ""
            ]
            if let fallbackData = try? JSONSerialization.data(withJSONObject: fallback, options: []),
               let fallbackStr = String(data: fallbackData, encoding: .utf8) {
                print(fallbackStr)
            }
            semaphore.signal()
            return
        }

        guard let data = data else {
            print("{\"error\": \"No data from Ollama\", \"raw_ocr\": \"\(ocrText.replacingOccurrences(of: "\"", with: "\\\""))\"}")
            semaphore.signal()
            return
        }

        if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let extraction = json["response"] as? String {
            
            debugPrint("--- Ollama Raw Response ---")
            debugPrint(extraction)
            debugPrint("--- End ---")
            
            // Clean up the extraction string (Ollama sometimes adds markdown or preamble text)
            var cleanExtraction = extraction.trimmingCharacters(in: .whitespacesAndNewlines)
            if cleanExtraction.hasPrefix("```json") {
                cleanExtraction = cleanExtraction.replacingOccurrences(of: "```json", with: "")
                cleanExtraction = cleanExtraction.replacingOccurrences(of: "```", with: "")
            } else if cleanExtraction.hasPrefix("```") {
                cleanExtraction = cleanExtraction.replacingOccurrences(of: "```", with: "")
            }

            var result = cleanExtraction.trimmingCharacters(in: .whitespacesAndNewlines)
            if let start = result.firstIndex(of: "{"),
               let end = result.lastIndex(of: "}") {
                result = String(result[start...end]).trimmingCharacters(in: .whitespacesAndNewlines)
            }

            // Try to parse it and add raw_ocr
            if let resultData = result.data(using: .utf8),
               var jsonDict = try? JSONSerialization.jsonObject(with: resultData) as? [String: Any] {
                jsonDict = normalizeExtractedFields(jsonDict, rawOCR: ocrText)
                if let finalData = try? JSONSerialization.data(withJSONObject: jsonDict, options: []),
                   let finalStr = String(data: finalData, encoding: .utf8) {
                    print(finalStr)
                }
            } else {
                // If LLM output isn't perfect JSON, wrap it
                let fallback: [String: Any] = [
                    "raw_ocr": ocrText,
                    "raw_response": result,
                    "name": "", "title": "", "company": "", "email": "", "phone": "", "address": ""
                ]
                var normalized = normalizeExtractedFields(fallback, rawOCR: ocrText)
                normalized["raw_response"] = result
                if let fallbackData = try? JSONSerialization.data(withJSONObject: normalized, options: []),
                   let fallbackStr = String(data: fallbackData, encoding: .utf8) {
                    print(fallbackStr)
                }
            }
        } else {
            print("{\"error\": \"Failed to parse Ollama response\", \"raw_ocr\": \"\(ocrText.replacingOccurrences(of: "\"", with: "\\\""))\"}")
        }
        semaphore.signal()
    }

    task.resume()
    semaphore.wait()

} catch {
    print("{\"error\": \"\(error.localizedDescription)\"}")
    exit(1)
}
