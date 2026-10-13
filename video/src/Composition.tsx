import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

// Grade cinematográfica: contraste, dessaturação leve, tons quentes nos
// realces e frios nas sombras, além de vinheta.
const GRADE_FILTER = "contrast(1.12) saturate(0.88) brightness(0.96) sepia(0.06)";

const Grade: React.FC = () => (
  <>
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(180deg, rgba(20,60,80,0.35) 0%, rgba(0,0,0,0) 45%, rgba(255,140,60,0.22) 100%)",
        mixBlendMode: "soft-light",
      }}
    />
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.6) 100%)",
      }}
    />
  </>
);

const Motivation: React.FC<{ text: string; from: number; to: number }> = ({
  text,
  from,
  to,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const local = frame - from;
  const scale = spring({ frame: local, fps, config: { damping: 14 } });
  const opacity = interpolate(frame, [from, from + 10, to - 12, to], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  if (frame < from || frame > to) return null;
  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        padding: 80,
        opacity,
      }}
    >
      <div
        style={{
          transform: `scale(${0.9 + 0.1 * scale})`,
          color: "#fff",
          fontFamily: "Helvetica Neue, Arial, sans-serif",
          fontWeight: 800,
          fontSize: 92,
          lineHeight: 1.05,
          textAlign: "center",
          textTransform: "uppercase",
          letterSpacing: 2,
          textShadow: "0 6px 30px rgba(0,0,0,0.7)",
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};

// Destaque tipo "lower third" com fade in/out.
const Highlight: React.FC<{ title: string; sub: string; from: number; to: number }> = ({
  title,
  sub,
  from,
  to,
}) => {
  const frame = useCurrentFrame();
  if (frame < from || frame > to) return null;
  const opacity = interpolate(frame, [from, from + 12, to - 12, to], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const x = interpolate(frame, [from, from + 14], [-40, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        position: "absolute",
        left: 60,
        bottom: 260,
        opacity,
        transform: `translateX(${x}px)`,
        borderLeft: "8px solid #ff8c3c",
        paddingLeft: 24,
        color: "#fff",
        fontFamily: "Helvetica Neue, Arial, sans-serif",
        textShadow: "0 4px 20px rgba(0,0,0,0.8)",
      }}
    >
      <div style={{ fontSize: 64, fontWeight: 800, textTransform: "uppercase" }}>{title}</div>
      <div style={{ fontSize: 38, fontWeight: 400, marginTop: 6 }}>{sub}</div>
    </div>
  );
};

// Foto com Ken Burns lento (zoom + deriva) e grade.
const PhotoScene: React.FC<{ src: string; durationInFrames: number }> = ({
  src,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, durationInFrames], [1.0, 1.12]);
  const drift = interpolate(frame, [0, durationInFrames], [0, -30]);
  return (
    <AbsoluteFill style={{ backgroundColor: "#000", overflow: "hidden" }}>
      <AbsoluteFill style={{ filter: GRADE_FILTER }}>
        <Img
          src={staticFile(src)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: `scale(${scale}) translateX(${drift}px)`,
          }}
        />
      </AbsoluteFill>
      <Grade />
    </AbsoluteFill>
  );
};

// Clipe de vídeo com grade e fade do início/fim.
const VideoScene: React.FC<{ src: string; durationInFrames: number }> = ({
  src,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const fade = interpolate(frame, [0, 15, durationInFrames - 15, durationInFrames], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ backgroundColor: "#000", opacity: fade }}>
      <AbsoluteFill style={{ filter: GRADE_FILTER }}>
        <OffthreadVideo src={staticFile(src)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </AbsoluteFill>
      <Grade />
    </AbsoluteFill>
  );
};

const Title: React.FC<{ title: string; sub: string }> = ({ title, sub }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 18 } });
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: 60 }}>
      <div
        style={{
          transform: `translateY(${(1 - s) * 60}px)`,
          opacity: s,
          textAlign: "center",
          color: "#fff",
          fontFamily: "Helvetica Neue, Arial, sans-serif",
          textShadow: "0 6px 30px rgba(0,0,0,0.8)",
        }}
      >
        <div style={{ fontSize: 120, fontWeight: 900, letterSpacing: 6 }}>{title}</div>
        <div style={{ fontSize: 48, marginTop: 20, color: "#ffb37a" }}>{sub}</div>
      </div>
    </AbsoluteFill>
  );
};

export const TriatloMotivacional: React.FC = () => {
  // Linha do tempo (em frames a 30 fps)
  const A = 90; // título sobre foto (3s)
  const B = 610; // clipe 1 (~20,3s)
  const C = 195; // clipe 2 (6,5s)
  const D = 4 * 90; // montagem de fotos (4 × 3s)
  const E = 120; // encerramento (4s)

  const startB = A;
  const startC = startB + B;
  const startD = startC + C;
  const startE = startD + D;

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <Sequence durationInFrames={A}>
        <PhotoScene src="6ee6b978.jpg" durationInFrames={A} />
        <Title title="TRIATLO" sub="Treino de bike · Indoor" />
      </Sequence>

      <Sequence from={startB} durationInFrames={B}>
        <VideoScene src="clip1.mp4" durationInFrames={B} />
        <Highlight title="Posição aero" sub="Cotovelos apoiados, tronco estável" from={0} to={120} />
        <Highlight title="Cadência constante" sub="Pedalada redonda e fluida" from={180} to={320} />
        <Highlight title="Foco no ajuste" sub="Freios e guidão alinhados" from={380} to={500} />
        <Motivation text="Cada pedalada te aproxima da linha de chegada." from={520} to={600} />
      </Sequence>

      <Sequence from={startC} durationInFrames={C}>
        <VideoScene src="clip2.mp4" durationInFrames={C} />
        <Motivation text="O cansaço passa. O orgulho fica." from={0} to={190} />
      </Sequence>

      <Sequence from={startD} durationInFrames={D}>
        <Sequence durationInFrames={90}>
          <PhotoScene src="c495cab8.jpg" durationInFrames={90} />
          <Motivation text="Constância vence talento." from={0} to={85} />
        </Sequence>
        <Sequence from={90} durationInFrames={90}>
          <PhotoScene src="0400d537.jpg" durationInFrames={90} />
          <Motivation text="Disciplina é treinar quando ninguém vê." from={0} to={85} />
        </Sequence>
        <Sequence from={180} durationInFrames={90}>
          <PhotoScene src="f03151f7.jpg" durationInFrames={90} />
          <Motivation text="Força se constrói no sofrimento." from={0} to={85} />
        </Sequence>
        <Sequence from={270} durationInFrames={90}>
          <PhotoScene src="b7820826.jpg" durationInFrames={90} />
          <Motivation text="Respire. Ajuste. Continue." from={0} to={85} />
        </Sequence>
      </Sequence>

      <Sequence from={startE} durationInFrames={E}>
        <AbsoluteFill style={{ backgroundColor: "#000" }}>
          <Title title="Hoje treina." sub="Amanhã compete." />
        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>
  );
};
