import Foundation

let REGISTER_QUEUE = "face_register_tasks"
let RECOGNIZE_QUEUE = "face_recognize_tasks"
let STATUS_PREFIX = "face_status:"
let PYTHON_BIN = ProcessInfo.processInfo.environment["PYTHON_BIN"] ?? "python3"
let SCRIPT_DIR = URL(fileURLWithPath: #file).deletingLastPathComponent()
let HELPER_PATH = SCRIPT_DIR.deletingLastPathComponent().appendingPathComponent("helpers").appendingPathComponent("face_worker_helper.py").path

func debugPrint(_ message: String) {
    if let data = (message + "\n").data(using: .utf8) {
        FileHandle.standardError.write(data)
    }
}

func runCommand(_ args: [String]) -> String? {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
    process.arguments = args
    let outputPipe = Pipe()
    process.standardOutput = outputPipe
    let errorPipe = Pipe()
    process.standardError = errorPipe

    do {
        try process.run()
        process.waitUntilExit()
    } catch {
        return nil
    }

    let data = outputPipe.fileHandleForReading.readDataToEndOfFile()
    if let output = String(data: data, encoding: .utf8), !output.isEmpty {
        return output.trimmingCharacters(in: .whitespacesAndNewlines)
    }
    let errData = errorPipe.fileHandleForReading.readDataToEndOfFile()
    return String(data: errData, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines)
}

func runRedisCommand(_ args: [String]) -> String? {
    return runCommand(["redis-cli", "--raw"] + args)
}

func updateStatus(taskId: String, payload: [String: Any]) {
    guard let data = try? JSONSerialization.data(withJSONObject: payload, options: []),
          let jsonStr = String(data: data, encoding: .utf8) else {
        return
    }
    _ = runRedisCommand(["setex", "\(STATUS_PREFIX)\(taskId)", "3600", jsonStr])
}

func invokeHelper(task: [String: Any]) -> [String: Any] {
    guard let type = task["type"] as? String,
          let imagePath = task["image_path"] as? String else {
        return ["ok": false, "error": "Invalid task payload"]
    }

    let pythonBin = (task["python_bin"] as? String).flatMap { $0.isEmpty ? nil : $0 } ?? PYTHON_BIN
    var args = [pythonBin, HELPER_PATH, "--type", type, "--image-path", imagePath]
    if let registrationId = task["registration_id"] as? String, !registrationId.isEmpty {
        args.append(contentsOf: ["--registration-id", registrationId])
    }
    if let threshold = task["threshold"] {
        args.append(contentsOf: ["--threshold", "\(threshold)"])
    }

    guard let output = runCommand(args), !output.isEmpty else {
        return ["ok": false, "error": "Face helper returned empty output"]
    }
    guard let data = output.data(using: .utf8),
          let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
        return [
            "ok": false,
            "error": "Face helper returned non-JSON output",
            "raw_output": output
        ]
    }
    return json
}

func processTask(task: [String: Any]) {
    guard let taskId = task["task_id"] as? String,
          let type = task["type"] as? String else {
        return
    }

    var processing: [String: Any] = [
        "task_id": taskId,
        "type": type,
        "status": "processing",
        "updated_at": Date().timeIntervalSince1970
    ]
    if let registrationId = task["registration_id"] as? String {
        processing["registration_id"] = registrationId
    }
    updateStatus(taskId: taskId, payload: processing)

    let result = invokeHelper(task: task)
    var finalPayload = processing
    finalPayload["updated_at"] = Date().timeIntervalSince1970

    if let ok = result["ok"] as? Bool, ok {
        finalPayload["status"] = "done"
        finalPayload["matched"] = result["matched"] as? Bool ?? false
        finalPayload["visitor"] = result["visitor"] ?? NSNull()
        finalPayload["score"] = result["score"] ?? 0
        finalPayload["quality_score"] = result["quality_score"] ?? NSNull()
        finalPayload["top_matches"] = result["top_matches"] ?? []
        finalPayload["result"] = result
    } else {
        finalPayload["status"] = "error"
        finalPayload["error"] = result["error"] ?? "Unknown face worker error"
        if let rawOutput = result["raw_output"] {
            finalPayload["raw_output"] = rawOutput
        }
    }

    updateStatus(taskId: taskId, payload: finalPayload)
    let matched = finalPayload["matched"] ?? false
    let score = finalPayload["score"] ?? 0
    debugPrint("Completed face task \(taskId) type=\(type) matched=\(matched) score=\(score)")
}

func listen(queue: String) {
    debugPrint("Swift Face Redis Worker listening on \(queue)")
    while true {
        if let output = runRedisCommand(["BLPOP", queue, "1"]) {
            let lines = output.components(separatedBy: .newlines)
            if lines.count >= 2 {
                let jsonStr = lines[1]
                if let data = jsonStr.data(using: .utf8),
                   let task = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    processTask(task: task)
                } else {
                    debugPrint("Failed to parse face BLPOP payload as JSON: \(jsonStr)")
                }
            } else if !output.isEmpty {
                debugPrint("Unexpected face BLPOP output: \(output)")
            }
        }
        Thread.sleep(forTimeInterval: 0.05)
    }
}

DispatchQueue.global().async {
    listen(queue: REGISTER_QUEUE)
}

listen(queue: RECOGNIZE_QUEUE)
