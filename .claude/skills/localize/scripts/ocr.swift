import Foundation
import Vision
import AppKit
let dir = CommandLine.arguments[1]
let files = try! FileManager.default.contentsOfDirectory(atPath: dir).filter{$0.hasSuffix(".jpg")}.sorted()
var out: [[String: Any]] = []
let q = DispatchQueue(label: "o")
DispatchQueue.concurrentPerform(iterations: files.count) { i in
  let f = files[i]
  guard let img = NSImage(contentsOfFile: dir + "/" + f), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { return }
  let req = VNRecognizeTextRequest()
  req.recognitionLevel = .accurate
  req.recognitionLanguages = ["en-US"]
  req.usesLanguageCorrection = true
  try? VNImageRequestHandler(cgImage: cg).perform([req])
  var items: [[String: Any]] = []
  for r in req.results ?? [] {
    guard let c = r.topCandidates(1).first else { continue }
    let b = r.boundingBox
    items.append(["text": c.string, "conf": c.confidence,
      "x0": b.minX * Double(cg.width), "x1": b.maxX * Double(cg.width),
      "y0": (1 - b.maxY) * Double(cg.height), "y1": (1 - b.minY) * Double(cg.height)])
  }
  q.sync { out.append(["file": f, "items": items]) }
}
let data = try! JSONSerialization.data(withJSONObject: out.sorted{ ($0["file"] as! String) < ($1["file"] as! String) }, options: [])
FileManager.default.createFile(atPath: CommandLine.arguments[2], contents: data)
print("frames", out.count)
