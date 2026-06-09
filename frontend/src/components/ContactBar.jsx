import { ExternalLink, Mail, MapPin, MessageCircle, Phone } from "lucide-react";

export default function ContactBar() {
  return (
    <div className="contact-bar" aria-label="Dados de contato">
      <span className="contact-name">Gabriel Camim Santos</span>
      <a href="mailto:camim2003@gmail.com?subject=Recrutamento" title="Enviar email">
        <Mail size={15} aria-hidden="true" />
        <span>Camim2003@gmail.com</span>
      </a>
      <a href="https://wa.link/rixmac" target="_blank" rel="noreferrer" title="Chamar no WhatsApp">
        <Phone size={15} aria-hidden="true" />
        <span>+55 (11) 95804-8353</span>
      </a>
      <span className="contact-location" title="Localização">
        <MapPin size={15} aria-hidden="true" />
        <span>São Paulo, SP - Brasil</span>
      </span>
      <a
        href="https://www.linkedin.com/in/gabriel-camim-681323215/"
        target="_blank"
        rel="noreferrer"
        title="Abrir LinkedIn"
      >
        <ExternalLink size={15} aria-hidden="true" />
        <span>LinkedIn</span>
      </a>
      <a href="https://wa.link/rixmac" target="_blank" rel="noreferrer" title="Abrir WhatsApp">
        <MessageCircle size={15} aria-hidden="true" />
        <span>WhatsApp</span>
      </a>
    </div>
  );
}
