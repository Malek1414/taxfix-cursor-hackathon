import SwiftUI
import AVFoundation
import UIKit

// Taxfix's own document-capture look (App Store shot 4): pale lime ground, corner brackets, one green shutter.
final class CameraController: NSObject, ObservableObject, AVCapturePhotoCaptureDelegate {
    let session = AVCaptureSession()
    private let output = AVCapturePhotoOutput()
    private var onPhoto: ((UIImage) -> Void)?
    @Published var ready = false

    func start() {
        guard !session.isRunning else { return }
        AVCaptureDevice.requestAccess(for: .video) { ok in
            guard ok, let dev = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back),
                  let input = try? AVCaptureDeviceInput(device: dev) else { return }
            self.session.beginConfiguration(); self.session.sessionPreset = .photo
            if self.session.canAddInput(input) { self.session.addInput(input) }
            if self.session.canAddOutput(self.output) { self.session.addOutput(self.output) }
            self.session.commitConfiguration()
            DispatchQueue.global(qos: .userInitiated).async { self.session.startRunning(); DispatchQueue.main.async { self.ready = true } }
        }
    }
    func stop() { if session.isRunning { session.stopRunning() } }
    func capture(_ done: @escaping (UIImage) -> Void) {
        onPhoto = done
        let s = AVCapturePhotoSettings(); s.flashMode = .off
        output.capturePhoto(with: s, delegate: self)
    }
    func photoOutput(_ o: AVCapturePhotoOutput, didFinishProcessingPhoto photo: AVCapturePhoto, error: Error?) {
        guard let d = photo.fileDataRepresentation(), let img = UIImage(data: d) else { return }
        DispatchQueue.main.async { self.onPhoto?(img) }
    }
}

struct PreviewLayer: UIViewRepresentable {
    let session: AVCaptureSession
    func makeUIView(context: Context) -> PreviewView { let v = PreviewView(); v.layer.session = session; v.layer.videoGravity = .resizeAspectFill; return v }
    func updateUIView(_ v: PreviewView, context: Context) {}
    final class PreviewView: UIView { override class var layerClass: AnyClass { AVCaptureVideoPreviewLayer.self }
        var layer_: AVCaptureVideoPreviewLayer { layer as! AVCaptureVideoPreviewLayer }
        override var layer: AVCaptureVideoPreviewLayer { super.layer as! AVCaptureVideoPreviewLayer } }
}

struct CornerFrame: View {
    var body: some View {
        GeometryReader { g in
            let w = g.size.width, h = g.size.height, l: CGFloat = 34, t: CGFloat = 5
            Path { p in
                for (x, y, dx, dy) in [(0, 0, 1, 1), (w, 0, -1, 1), (0, h, 1, -1), (w, h, -1, -1)] as [(CGFloat, CGFloat, CGFloat, CGFloat)] {
                    p.move(to: CGPoint(x: x, y: y + dy * l)); p.addLine(to: CGPoint(x: x, y: y)); p.addLine(to: CGPoint(x: x + dx * l, y: y))
                }
            }.stroke(Color.green, style: StrokeStyle(lineWidth: t, lineCap: .round, lineJoin: .round))
        }
    }
}

struct ScanCameraView: View {
    @StateObject private var cam = CameraController()
    @State private var flash = false
    var onImage: (UIImage) -> Void
    var body: some View {
        VStack(spacing: 0) {
            Text("Photograph the receipt").font(.system(size: 20, weight: .heavy)).padding(.top, 8)
            Text("While it's still in your hand. We read merchant, total and VAT on this phone.").font(.system(size: 13)).foregroundStyle(.secondary).multilineTextAlignment(.center).padding(.horizontal, 32).padding(.top, 4)
            ZStack {
                RoundedRectangle(cornerRadius: 22).fill(Color(red: 0.90, green: 0.98, blue: 0.80))
                Group {
                    if cam.ready { PreviewLayer(session: cam.session).clipShape(RoundedRectangle(cornerRadius: 14)) }
                    else { RoundedRectangle(cornerRadius: 14).fill(Color.white).overlay(ProgressView().tint(Color.green)) }
                }.padding(.horizontal, 44).padding(.vertical, 40)
                CornerFrame().padding(.horizontal, 30).padding(.vertical, 26)
                if flash { RoundedRectangle(cornerRadius: 22).fill(.white).transition(.opacity) }
            }.padding(16).frame(maxHeight: .infinity)
            Button {
                withAnimation(.easeOut(duration: 0.08)) { flash = true }
                cam.capture { img in withAnimation { flash = false }; cam.stop(); onImage(img) }
            } label: {
                ZStack { Circle().fill(.white).frame(width: 78, height: 78).shadow(color: .black.opacity(0.15), radius: 8, y: 3)
                         Circle().fill(Color.green).frame(width: 64, height: 64)
                         Image(systemName: "camera.fill").foregroundStyle(.white).font(.system(size: 22, weight: .semibold)) }
            }.buttonStyle(.plain).padding(.bottom, 28).disabled(!cam.ready)
        }
        .background(Color.white)
        .onAppear { cam.start() }.onDisappear { cam.stop() }
    }
}
