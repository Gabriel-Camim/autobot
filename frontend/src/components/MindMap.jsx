import {
  Brain,
  BriefcaseBusiness,
  FileArchive,
  FolderKanban,
  Layers3,
  MessageSquareText,
  Play,
  Route,
  TrendingUp,
} from "lucide-react";

export const MIND_MAP_NODES = [
  {
    id: "gabriel",
    label: "Gabriel",
    summary: "Perfil, personalidade, valores e forma de pensar.",
    icon: Brain,
    x: 50,
    y: 51,
    accent: "#0f766e",
  },
  {
    id: "trajetoria",
    label: "Trajetória",
    summary: "Linha do tempo, formação e idiomas.",
    icon: Route,
    x: 20,
    y: 23,
    accent: "#b45309",
  },
  {
    id: "projetos",
    label: "Projetos",
    summary: "Autobot, DGE, Ebook Generator e veterinária.",
    icon: FolderKanban,
    x: 80,
    y: 25,
    accent: "#be123c",
  },
  {
    id: "stack",
    label: "Stack",
    summary: "Python, FastAPI, LangChain, Chroma, OpenAI e React.",
    icon: Layers3,
    x: 17,
    y: 68,
    accent: "#2563eb",
  },
  {
    id: "experiencia",
    label: "Experiência",
    summary: "Experiências, desafios e aprendizados.",
    icon: BriefcaseBusiness,
    x: 48,
    y: 84,
    accent: "#7c3aed",
  },
  {
    id: "mercado",
    label: "Mercado",
    summary: "Visão de mercado e tipos de problema.",
    icon: TrendingUp,
    x: 83,
    y: 66,
    accent: "#0e7490",
  },
  {
    id: "entrevista",
    label: "Entrevista",
    summary: "FAQ, experiências marcantes e perguntas técnicas.",
    icon: MessageSquareText,
    x: 50,
    y: 17,
    accent: "#15803d",
  },
  {
    id: "materiais",
    label: "Materiais",
    summary: "Pacote recrutador e documentos curados.",
    icon: FileArchive,
    x: 20,
    y: 47,
    accent: "#c2410c",
  },
];

export default function MindMap({ activeNode, onSelect, onPlayReport }) {
  const center = MIND_MAP_NODES.find((node) => node.id === "gabriel");

  return (
    <div className="mind-map">
      <svg className="mind-map-lines" viewBox="0 0 100 100" aria-hidden="true">
        {MIND_MAP_NODES.filter((node) => node.id !== "gabriel").map((node) => (
          <line
            key={node.id}
            x1={center.x}
            y1={center.y}
            x2={node.x}
            y2={node.y}
            vectorEffect="non-scaling-stroke"
          />
        ))}
      </svg>
      {MIND_MAP_NODES.map((node) => {
        const Icon = node.icon;
        return (
          <div
            key={node.id}
            title={node.summary}
            className={`map-node ${activeNode === node.id ? "is-active" : ""}`}
            style={{ "--x": `${node.x}%`, "--y": `${node.y}%`, "--accent": node.accent }}
          >
            <button className="node-main" type="button" onClick={() => onSelect(node.id)}>
              <span className="node-icon">
                <Icon size={20} strokeWidth={2.2} aria-hidden="true" />
              </span>
              <span className="node-copy">
                <strong>{node.label}</strong>
                <small>{node.summary}</small>
              </span>
            </button>
            <button
              type="button"
              className="node-play"
              title={`Abrir relatório: ${node.label}`}
              onClick={() => onPlayReport(node.id)}
            >
              <Play size={15} fill="currentColor" aria-hidden="true" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
