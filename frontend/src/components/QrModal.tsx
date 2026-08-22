import QRCode from 'react-qr-code';
import { X } from 'lucide-react';
import { MonoLabel } from './badges';

interface Props {
  tagId: string;
  qrCode: string;
  onClose: () => void;
}

/** Printable supply-chain QR for one animal — scan → public trace page. */
export default function QrModal({ tagId, qrCode, onClose }: Props) {
  const url = `${window.location.origin}/trace/${qrCode}`;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="w-full max-w-sm rounded-3xl bg-surface-container-lowest p-6 text-center shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between">
          <MonoLabel className="pt-1 text-primary">Farm-to-consumer QR</MonoLabel>
          <button
            onClick={onClose}
            className="rounded-full p-1.5 text-on-surface-variant hover:bg-surface-container-high"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <h3 className="font-mono text-lg font-bold text-on-surface">{tagId}</h3>
        <div className="mx-auto mt-3 w-fit rounded-2xl border border-outline-variant/40 bg-white p-3">
          <QRCode value={url} size={200} />
        </div>
        <p className="mt-3 break-all rounded-xl bg-surface-container p-2 font-mono text-[11px] text-on-surface-variant">
          {url}
        </p>
        <a
          href={`/trace/${qrCode}`}
          target="_blank"
          rel="noreferrer"
          className="mt-4 block rounded-2xl bg-primary py-2.5 text-sm font-semibold text-on-primary shadow-md transition-colors hover:bg-primary-container"
        >
          Open public trace page ↗
        </a>
        <p className="mt-3 text-[11px] leading-snug text-outline">
          Print this on the animal's card / ear-tag backup. Anyone scanning it sees the full medicine
          &amp; residue history — no login needed.
        </p>
      </div>
    </div>
  );
}
