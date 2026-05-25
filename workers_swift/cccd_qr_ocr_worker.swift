import Foundation
import Vision
import AppKit

func printJSON(_ obj: [String: Any]) {
    if let data = try? JSONSerialization.data(withJSONObject: obj, options: []),
       let text = String(data: data, encoding: .utf8) {
        print(text)
    } else {
        print("{\"ok\":false,\"error\":\"json_encode_failed\"}")
    }
}

func trim(_ value: String) -> String {
    value.trimmingCharacters(in: .whitespacesAndNewlines)
}

func digitsOnly(_ value: String) -> String {
    value.replacingOccurrences(of: "[^0-9]", with: "", options: .regularExpression)
}

func toISODate(_ raw: String) -> String {
    let digits = digitsOnly(raw)
    guard digits.count == 8 else { return trim(raw) }
    let dd = digits.prefix(2)
    let mm = digits.dropFirst(2).prefix(2)
    let yyyy = digits.dropFirst(4)
    return "\(yyyy)-\(mm)-\(dd)"
}

func parseVNIdQr(_ raw: String) -> [String: String] {
    let parts = raw.split(separator: "|", omittingEmptySubsequences: false).map { trim(String($0)) }
    guard parts.count >= 7 else { return [:] }
    let idNumber = digitsOnly(parts[0])
    guard (9...12).contains(idNumber.count) else { return [:] }

    var gender = parts[4]
    if ["m", "nam"].contains(gender.lowercased()) { gender = "Nam" }
    if ["f", "nu", "nữ"].contains(gender.lowercased()) { gender = "Nữ" }

    return [
        "idNumber": idNumber,
        "oldId": parts[1],
        "fullName": parts[2],
        "dob": toISODate(parts[3]),
        "gender": gender,
        "address": parts[5],
        "expiry": toISODate(parts[6]),
    ]
}

func parseIssuedDate(from text: String) -> String {
    let patterns = [
        "(?i)(ngay cap|date of issue)\\s*[:\\-]?\\s*(\\d{1,2}[\\/\\-]\\d{1,2}[\\/\\-]\\d{4})",
        "(?i)(cap ngay)\\s*[:\\-]?\\s*(\\d{1,2}[\\/\\-]\\d{1,2}[\\/\\-]\\d{4})",
    ]
    for pattern in patterns {
        if let regex = try? NSRegularExpression(pattern: pattern),
           let match = regex.firstMatch(in: text, range: NSRange(text.startIndex..., in: text)),
           match.numberOfRanges > 2,
           let range = Range(match.range(at: 2), in: text) {
            return toISODate(String(text[range]))
        }
    }
    return ""
}

func matchFirst(_ pattern: String, in text: String, group: Int = 1) -> String {
    guard let regex = try? NSRegularExpression(pattern: pattern, options: []) else { return "" }
    guard let match = regex.firstMatch(in: text, range: NSRange(text.startIndex..., in: text)) else { return "" }
    guard match.numberOfRanges > group else { return "" }
    guard let range = Range(match.range(at: group), in: text) else { return "" }
    return trim(String(text[range]))
}

func parseName(from text: String) -> String {
    let patterns = [
        "(?is)(?:full\\s*name|ho,?\\s*chu.*?ten\\s*khai\\s*sinh)\\s*[:\\-]?\\s*\\n\\s*([^\\n]+)",
        "(?im)^([A-ZÀ-Ỹ][A-ZÀ-Ỹ\\s]{5,})$",
    ]
    for pattern in patterns {
        let value = matchFirst(pattern, in: text)
        if !value.isEmpty, value.lowercased() != "việt nam" {
            return value
        }
    }
    return ""
}

func parseDob(from text: String) -> String {
    let value = matchFirst("(?is)(?:date\\s*of\\s*birth|ngay,?\\s*thang,?\\s*nam\\s*sinh)\\s*[:\\-]?\\s*\\n?\\s*(\\d{1,2}[\\/\\-]\\d{1,2}[\\/\\-]\\d{4})", in: text)
    return value.isEmpty ? "" : toISODate(value)
}

func parseGender(from text: String) -> String {
    let value = matchFirst("(?is)(?:gioi\\s*tinh|sex)\\s*[:\\-]?\\s*\\n?\\s*([^\\n]+)", in: text)
    let lower = value.lowercased()
    if lower.contains("nam") || lower == "m" || lower.contains("male") { return "Nam" }
    if lower.contains("nữ") || lower.contains("nu") || lower == "f" || lower.contains("female") { return "Nữ" }
    return value
}

func parseAddress(from text: String) -> String {
    let patterns = [
        "(?is)(?:place\\s*of\\s*residence|noi\\s*thuong\\s*tru)\\s*[:\\-]?\\s*\\n\\s*([^\\n]+(?:\\n(?!ngay|gioi|sex|quoc\\s*tich|nationality|co\\s*gia\\s*tri|date\\s*of).+)*)",
        "(?is)(?:place\\s*of\\s*residence|noi\\s*thuong\\s*tru)\\s*[:\\-]?\\s*\\n?\\s*([^\\n]+)",
    ]
    for pattern in patterns {
        let value = matchFirst(pattern, in: text)
        if !value.isEmpty {
            return value.replacingOccurrences(of: "\\s*\\n\\s*", with: ", ", options: .regularExpression)
        }
    }
    return ""
}

func loadCGImage(from imagePath: String) -> CGImage? {
    let imageUrl = URL(fileURLWithPath: imagePath)
    guard let image = NSImage(contentsOf: imageUrl),
          let tiffData = image.tiffRepresentation,
          let cgImage = NSBitmapImageRep(data: tiffData)?.cgImage else {
        return nil
    }
    return cgImage
}

func recognizeBarcode(from cgImage: CGImage) throws -> String {
    let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    let request = VNDetectBarcodesRequest()
    request.symbologies = [.qr]
    try handler.perform([request])

    let results = request.results ?? []
    for item in results {
        if let value = item.payloadStringValue, !trim(value).isEmpty {
            return trim(value)
        }
    }
    return ""
}

func recognizeText(from cgImage: CGImage) throws -> String {
    let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    request.recognitionLanguages = ["vi-VN", "en-US"]
    try handler.perform([request])

    let recognizedStrings = (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }
    return trim(recognizedStrings.joined(separator: "\n"))
}

guard CommandLine.arguments.count > 1 else {
    printJSON(["ok": false, "error": "Usage: swift cccd_qr_ocr_worker.swift <image_path>"])
    exit(1)
}

let imagePath = CommandLine.arguments[1]
guard FileManager.default.fileExists(atPath: imagePath) else {
    printJSON(["ok": false, "error": "File not found"])
    exit(1)
}

guard let cgImage = loadCGImage(from: imagePath) else {
    printJSON(["ok": false, "error": "Failed to load image"])
    exit(1)
}

let resultQueue = DispatchQueue(label: "cccd.worker.result")
let group = DispatchGroup()

var qrRaw = ""
var ocrText = ""
var barcodeError: String?
var textError: String?

group.enter()
DispatchQueue.global(qos: .userInitiated).async {
    defer { group.leave() }
    do {
        let value = try recognizeBarcode(from: cgImage)
        resultQueue.sync { qrRaw = value }
    } catch {
        resultQueue.sync { barcodeError = error.localizedDescription }
    }
}

group.enter()
DispatchQueue.global(qos: .userInitiated).async {
    defer { group.leave() }
    do {
        let value = try recognizeText(from: cgImage)
        resultQueue.sync { ocrText = value }
    } catch {
        resultQueue.sync { textError = error.localizedDescription }
    }
}

group.wait()

if !trim(qrRaw).isEmpty || !trim(ocrText).isEmpty {
    let parsedQr = parseVNIdQr(qrRaw)
    var data: [String: String] = [
        "idNumber": parsedQr["idNumber"] ?? "",
        "oldId": parsedQr["oldId"] ?? "",
        "fullName": parsedQr["fullName"] ?? "",
        "dob": parsedQr["dob"] ?? "",
        "gender": parsedQr["gender"] ?? "",
        "address": parsedQr["address"] ?? "",
        "expiry": parsedQr["expiry"] ?? "",
        "issued": "",
    ]

    if !ocrText.isEmpty {
        if data["issued"]?.isEmpty ?? true {
            data["issued"] = parseIssuedDate(from: ocrText)
        }

        if data["idNumber"]?.isEmpty ?? true {
            if let regex = try? NSRegularExpression(pattern: "\\b\\d{9,12}\\b"),
               let match = regex.firstMatch(in: ocrText, range: NSRange(ocrText.startIndex..., in: ocrText)),
               let range = Range(match.range(at: 0), in: ocrText) {
                data["idNumber"] = String(ocrText[range])
            }
        }

        if data["fullName"]?.isEmpty ?? true {
            data["fullName"] = parseName(from: ocrText)
        }
        if data["dob"]?.isEmpty ?? true {
            data["dob"] = parseDob(from: ocrText)
        }
        if data["gender"]?.isEmpty ?? true {
            data["gender"] = parseGender(from: ocrText)
        }
        if data["address"]?.isEmpty ?? true {
            data["address"] = parseAddress(from: ocrText)
        }
    }

    let lowerText = ocrText.lowercased()
    let keywordHits = [
        "can cuoc",
        "identity card",
        "citizen identity",
        "personal identification",
        "personal identification number",
        "full name",
        "date of birth",
        "sex",
        "ngay sinh",
        "gioi tinh",
        "noi thuong tru",
        "place of residence",
    ].filter { lowerText.contains($0) }
    let coreFieldCount = [
        data["idNumber", default: ""],
        data["fullName", default: ""],
        data["dob", default: ""],
        data["gender", default: ""],
        data["address", default: ""],
    ].filter { !trim($0).isEmpty }.count
    let hasCoreIdentity = !trim(data["idNumber", default: ""]).isEmpty && !trim(data["fullName", default: ""]).isEmpty
    let isCccd = !parsedQr.isEmpty || keywordHits.count >= 2 || (hasCoreIdentity && coreFieldCount >= 4)

    printJSON([
        "ok": true,
        "is_cccd": isCccd,
        "qr": [
            "raw": qrRaw,
            "parsed": parsedQr,
        ],
        "ocr": [
            "text": ocrText,
            "keywords": keywordHits,
        ],
        "data": data,
        "timing": [
            "mode": "parallel",
        ],
    ])
    exit(0)
}

let combinedError = [barcodeError, textError]
    .compactMap { $0 }
    .map { trim($0) }
    .filter { !$0.isEmpty }
    .joined(separator: " | ")

printJSON([
    "ok": false,
    "error": combinedError.isEmpty ? "No QR/OCR result" : combinedError,
])
exit(1)
