import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

const PHOTOS = [1, 2, 3, 4, 5, 6].map((number) => `/gallery/${number}.png`);

export default function GalleryModal({ open, onClose }) {
  const [index, setIndex] = useState(0);
  const slides = useMemo(() => ["note", ...PHOTOS], []);

  useEffect(() => {
    if (!open) return;

    function handleKey(event) {
      if (event.key === "Escape") onClose();
      if (event.key === "ArrowRight") setIndex((current) => Math.min(current + 1, slides.length - 1));
      if (event.key === "ArrowLeft") setIndex((current) => Math.max(current - 1, 0));
    }

    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose, open, slides.length]);

  useEffect(() => {
    if (open) setIndex(0);
  }, [open]);

  if (!open) return null;

  const current = slides[index];
  const canGoBack = index > 0;
  const canGoForward = index < slides.length - 1;

  return (
    <div className="gallery-modal" role="dialog" aria-modal="true" aria-label="Galeria de fotos">
      <div className="gallery-backdrop" onClick={onClose} />
      <div className="gallery-stage">
        <button className="gallery-close" type="button" title="Fechar galeria" onClick={onClose}>
          <X size={22} aria-hidden="true" />
        </button>
        <div className="phone-frame">
          <div className="phone-speaker" />
          <div className="phone-screen">
            {current === "note" ? (
              <div className="post-it">
                <span>Meus filhos &lt;3</span>
              </div>
            ) : (
              <img src={current} alt={`Foto ${index}`} />
            )}
          </div>
        </div>
        <button
          className="gallery-arrow left"
          type="button"
          title="Foto anterior"
          disabled={!canGoBack}
          onClick={() => setIndex((currentIndex) => Math.max(currentIndex - 1, 0))}
        >
          <ChevronLeft size={24} aria-hidden="true" />
        </button>
        <button
          className="gallery-arrow right"
          type="button"
          title="Próxima foto"
          disabled={!canGoForward}
          onClick={() => setIndex((currentIndex) => Math.min(currentIndex + 1, slides.length - 1))}
        >
          <ChevronRight size={24} aria-hidden="true" />
        </button>
        <div className="gallery-count">{index + 1} / {slides.length}</div>
      </div>
    </div>
  );
}
