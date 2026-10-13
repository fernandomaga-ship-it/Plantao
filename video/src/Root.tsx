import { Composition } from "remotion";
import { TriatloMotivacional } from "./Composition";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="TriatloMotivacional"
      component={TriatloMotivacional}
      durationInFrames={1375}
      fps={30}
      width={1080}
      height={1920}
    />
  );
};
