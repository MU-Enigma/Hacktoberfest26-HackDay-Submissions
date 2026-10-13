import { useEffect, useRef, useState } from "react";
import { Camera, CameraOff } from "lucide-react";
import { Html5Qrcode } from "html5-qrcode";
import { Button } from "@/components/ui/button";

export const tokenFromScan = (text) => {
  try {
    return new URL(text).searchParams.get("t") || text;
  } catch {
    return text;
  }
};

export function QrScanner({ onToken }) {
  const [on, setOn] = useState(false);
  const [err, setErr] = useState("");
  const ref = useRef(null);

  useEffect(() => {
    if (!on) return undefined;
    const qr = new Html5Qrcode("qr-reader");
    ref.current = qr;
    qr.start({ facingMode: "environment" }, { fps: 10, qrbox: 220 }, (text) => {
      qr.stop().catch(() => {});
      setOn(false);
      onToken(tokenFromScan(text));
    }).catch(() => {
      setErr("Camera unavailable. Enter the 6-digit code instead.");
      setOn(false);
    });
    return () => {
      if (qr.isScanning) qr.stop().catch(() => {});
    };
  }, [on, onToken]);

  return (
    <div className="space-y-2" data-testid="qr-scanner">
      <div id="qr-reader" className={`rounded-xl overflow-hidden ${on ? "" : "hidden"}`} />
      <Button variant="outline" onClick={() => { setErr(""); setOn(!on); }} data-testid="qr-scan-toggle">
        {on ? <><CameraOff className="h-4 w-4 mr-2" />Stop camera</> : <><Camera className="h-4 w-4 mr-2" />Scan QR with camera</>}
      </Button>
      {err && <p className="text-xs text-amber-700">{err}</p>}
    </div>
  );
}
