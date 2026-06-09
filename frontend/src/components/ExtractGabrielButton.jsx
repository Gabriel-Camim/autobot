import { Download } from "lucide-react";

export default function ExtractGabrielButton({ apiUrl, onError }) {
  async function downloadPackage() {
    try {
      const response = await fetch(`${apiUrl}/materials/extract-gabriel`);
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.message || "Não consegui baixar o pacote agora.");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "extrair-gabriel.zip";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      onError(error.message || "Não consegui baixar o pacote agora.");
    }
  }

  return (
    <button type="button" className="extract-button" title="Extrair Gabriel" onClick={downloadPackage}>
      <Download size={18} aria-hidden="true" />
      <span>Extrair Gabriel</span>
    </button>
  );
}
