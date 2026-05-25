import AppKit
import Foundation
import Vision

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(1)
}

func averagePoint(_ points: [CGPoint]) -> CGPoint? {
    guard !points.isEmpty else { return nil }
    let sum = points.reduce(CGPoint.zero) { partial, point in
        CGPoint(x: partial.x + point.x, y: partial.y + point.y)
    }
    let count = CGFloat(points.count)
    return CGPoint(x: sum.x / count, y: sum.y / count)
}

func normalizedPointToImage(_ point: CGPoint, in boundingBox: CGRect, imageWidth: CGFloat, imageHeight: CGFloat) -> [Double] {
    let globalX = (boundingBox.origin.x + point.x * boundingBox.size.width) * imageWidth
    let globalY = (1.0 - (boundingBox.origin.y + point.y * boundingBox.size.height)) * imageHeight
    return [Double(globalX), Double(globalY)]
}

func rectToTopLeftPixels(_ rect: CGRect, imageWidth: CGFloat, imageHeight: CGFloat) -> [String: Double] {
    let x = rect.origin.x * imageWidth
    let y = (1.0 - rect.origin.y - rect.size.height) * imageHeight
    return [
        "x": Double(x),
        "y": Double(y),
        "w": Double(rect.size.width * imageWidth),
        "h": Double(rect.size.height * imageHeight),
    ]
}

guard CommandLine.arguments.count > 1 else {
    fail("Usage: swift vision_face_detector.swift <image_path>")
}

let imagePath = CommandLine.arguments[1]
let imageUrl = URL(fileURLWithPath: imagePath)

guard FileManager.default.fileExists(atPath: imagePath) else {
    fail("File not found: \(imagePath)")
}

guard let image = NSImage(contentsOf: imageUrl),
      let tiffData = image.tiffRepresentation,
      let bitmap = NSBitmapImageRep(data: tiffData),
      let cgImage = bitmap.cgImage else {
    fail("Failed to load image")
}

let imageWidth = CGFloat(cgImage.width)
let imageHeight = CGFloat(cgImage.height)

let request = VNDetectFaceLandmarksRequest()
let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])

do {
    try handler.perform([request])
} catch {
    fail(error.localizedDescription)
}

guard let results = request.results else {
    fail("Vision returned no face results")
}

var faces: [[String: Any]] = []

for observation in results {
    let bbox = observation.boundingBox
    let bboxPixels = rectToTopLeftPixels(bbox, imageWidth: imageWidth, imageHeight: imageHeight)

    var leftEyePoint: CGPoint?
    var rightEyePoint: CGPoint?
    var nosePoint: CGPoint?
    var leftMouthPoint: CGPoint?
    var rightMouthPoint: CGPoint?

    if let landmarks = observation.landmarks {
        if let leftEye = landmarks.leftEye?.normalizedPoints, !leftEye.isEmpty {
            leftEyePoint = averagePoint(leftEye)
        }
        if let rightEye = landmarks.rightEye?.normalizedPoints, !rightEye.isEmpty {
            rightEyePoint = averagePoint(rightEye)
        }
        if let nose = landmarks.noseCrest?.normalizedPoints, !nose.isEmpty {
            nosePoint = averagePoint(nose)
        } else if let nose = landmarks.nose?.normalizedPoints, !nose.isEmpty {
            nosePoint = averagePoint(nose)
        }

        if let outerLips = landmarks.outerLips?.normalizedPoints, !outerLips.isEmpty {
            let sortedByX = outerLips.sorted { $0.x < $1.x }
            leftMouthPoint = sortedByX.first
            rightMouthPoint = sortedByX.last
        }
    }

    var landmarkPayload: [String: Any] = [:]
    var arcfaceLandmarks: [[Double]] = []

    if let leftEyePoint {
        landmarkPayload["left_eye"] = normalizedPointToImage(leftEyePoint, in: bbox, imageWidth: imageWidth, imageHeight: imageHeight)
    }
    if let rightEyePoint {
        landmarkPayload["right_eye"] = normalizedPointToImage(rightEyePoint, in: bbox, imageWidth: imageWidth, imageHeight: imageHeight)
    }
    if let nosePoint {
        landmarkPayload["nose"] = normalizedPointToImage(nosePoint, in: bbox, imageWidth: imageWidth, imageHeight: imageHeight)
    }
    if let leftMouthPoint {
        landmarkPayload["left_mouth"] = normalizedPointToImage(leftMouthPoint, in: bbox, imageWidth: imageWidth, imageHeight: imageHeight)
    }
    if let rightMouthPoint {
        landmarkPayload["right_mouth"] = normalizedPointToImage(rightMouthPoint, in: bbox, imageWidth: imageWidth, imageHeight: imageHeight)
    }

    for key in ["left_eye", "right_eye", "nose", "left_mouth", "right_mouth"] {
        if let point = landmarkPayload[key] as? [Double], point.count == 2 {
            arcfaceLandmarks.append(point)
        }
    }

    let area = (bboxPixels["w"] ?? 0.0) * (bboxPixels["h"] ?? 0.0)
    let confidence = observation.confidence

    faces.append(
        [
            "bbox": bboxPixels,
            "confidence": confidence,
            "area": area,
            "landmarks": landmarkPayload,
            "arcface_landmarks": arcfaceLandmarks,
        ]
    )
}

let payload: [String: Any] = [
    "ok": true,
    "image_size": [
        "w": Int(imageWidth),
        "h": Int(imageHeight),
    ],
    "faces": faces,
]

guard let data = try? JSONSerialization.data(withJSONObject: payload, options: []) else {
    fail("Failed to serialize Vision result")
}

FileHandle.standardOutput.write(data)
