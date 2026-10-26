import "./index.css";
import { Composition } from "remotion";
import { HelloWorld, myCompSchema } from "./HelloWorld";
import { Logo, myCompSchema2 } from "./HelloWorld/Logo";
import { SwissAlpsTour } from "./SwissTour/SwissAlpsTour";
import { AiroloFork } from "./SwissTour/AiroloFork";
import { DURATION, FPS } from "./SwissTour/timeline";
import { FORK_DURATION } from "./SwissTour/forkTimeline";
import { ColDeVars } from "./VarsTour/ColDeVars";
import { VARS_DURATION } from "./VarsTour/timeline";
import { Monginevro } from "./MonginevroTour/Monginevro";
import { MONGINEVRO_DURATION } from "./MonginevroTour/timeline";
import { ValStaffora } from "./OltrepoTour/ValStaffora";
import { OLTREPO_DURATION } from "./OltrepoTour/timeline";
import { GiovaBrallo } from "./BralloTour/GiovaBrallo";
import { GIOVA_BRALLO_DURATION } from "./BralloTour/timeline";
import { BralloBobbio } from "./BobbioTour/BralloBobbio";
import { BRALLO_BOBBIO_DURATION } from "./BobbioTour/timeline";
import { BobbioVarzi } from "./PeniceTour/BobbioVarzi";
import { PENICE_DURATION } from "./PeniceTour/timeline";
import { VarziTrebecco } from "./TrebeccoTour/VarziTrebecco";
import { TREBECCO_DURATION } from "./TrebeccoTour/timeline";
import { HookStradaIsolata, HOOK_DURATION } from "./Hook/HookStradaIsolata";
import { AdventouringTitle, TITLE_DURATION } from "./Title/AdventouringTitle";
import {
  AdventouringTitleMoto,
  TITLE_MOTO_DURATION,
} from "./Title/AdventouringTitleMoto";
import { VaubanOverlay, OVERLAY_DURATION } from "./Overlays/VaubanOverlay";
import { SeasonCard, SEASON_CARD_DURATION } from "./Seasons/SeasonCard";
import { SeasonMap, SEASON_MAP_DURATION } from "./Seasons/SeasonMap";
import { WinterFollow, WINTER_FOLLOW_DURATION } from "./Seasons/WinterFollow";
import {
  WinterQuestion,
  WINTER_QUESTION_DURATION,
} from "./Seasons/WinterQuestion";

// Each <Composition> is an entry in the sidebar!

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="SwissAlpsTour"
        component={SwissAlpsTour}
        durationInFrames={DURATION}
        fps={FPS}
        width={1080}
        height={1920}
      />

      <Composition
        id="AiroloFork"
        component={AiroloFork}
        durationInFrames={FORK_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
      />

      <Composition
        id="ColDeVars"
        component={ColDeVars}
        durationInFrames={VARS_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
      />

      <Composition
        id="Monginevro"
        component={Monginevro}
        durationInFrames={MONGINEVRO_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
      />

      <Composition
        id="ValStaffora"
        component={ValStaffora}
        durationInFrames={OLTREPO_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
      />

      <Composition
        id="GiovaBrallo"
        component={GiovaBrallo}
        durationInFrames={GIOVA_BRALLO_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
      />

      <Composition
        id="BralloBobbio"
        component={BralloBobbio}
        durationInFrames={BRALLO_BOBBIO_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
      />

      <Composition
        id="BobbioVarzi"
        component={BobbioVarzi}
        durationInFrames={PENICE_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
      />

      <Composition
        id="VarziTrebecco"
        component={VarziTrebecco}
        durationInFrames={TREBECCO_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
      />

      {/* Transparent overlay: render to ProRes 4444 or a PNG sequence, and
          to GIF with scripts/export_gif.py. */}
      <Composition
        id="HookStradaIsolata"
        component={HookStradaIsolata}
        durationInFrames={HOOK_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
      />

      {/* The series title: a transparent overlay like the hook. */}
      <Composition
        id="AdventouringTitle"
        component={AdventouringTitle}
        durationInFrames={TITLE_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
      />

      {/* The same title in a riding-film look. */}
      <Composition
        id="AdventouringTitleMoto"
        component={AdventouringTitleMoto}
        durationInFrames={TITLE_MOTO_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
      />

      {/* "4 stagioni, 4 tappe": season cards (transparent overlays), the
          stage maps (full screen) and the winter call to follow. */}
      <Composition
        id="SeasonCard-Primavera"
        component={SeasonCard}
        durationInFrames={SEASON_CARD_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          season: "PRIMAVERA",
          n: 1,
          place: "GORGES DU VERDON",
          stageId: "verdon",
        }}
      />
      <Composition
        id="SeasonCard-Estate"
        component={SeasonCard}
        durationInFrames={SEASON_CARD_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          season: "ESTATE",
          n: 2,
          place: "PASSO DELLA NOVENA",
          stageId: "novena",
        }}
      />
      <Composition
        id="SeasonCard-Autunno"
        component={SeasonCard}
        durationInFrames={SEASON_CARD_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          season: "AUTUNNO",
          n: 3,
          place: "VALLE STAFFORA",
          stageId: "staffora",
        }}
      />
      <Composition
        id="SeasonCard-Inverno"
        component={SeasonCard}
        durationInFrames={SEASON_CARD_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          season: "INVERNO",
          n: 4,
          place: "LA TAPPA SEGRETA",
          stageId: null,
        }}
      />
      <Composition
        id="SeasonMap-Verdon"
        component={SeasonMap}
        durationInFrames={SEASON_MAP_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{ stageId: "verdon" }}
      />
      <Composition
        id="SeasonMap-Novena"
        component={SeasonMap}
        durationInFrames={SEASON_MAP_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{ stageId: "novena" }}
      />
      <Composition
        id="SeasonMap-Staffora"
        component={SeasonMap}
        durationInFrames={SEASON_MAP_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{ stageId: "staffora" }}
      />
      <Composition
        id="WinterFollow"
        component={WinterFollow}
        durationInFrames={WINTER_FOLLOW_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
      />
      {/* Winter, chosen by the viewers: on the map, and as an overlay. */}
      <Composition
        id="WinterQuestion"
        component={WinterQuestion}
        durationInFrames={WINTER_QUESTION_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{ overlay: false }}
      />
      <Composition
        id="WinterQuestion-Overlay"
        component={WinterQuestion}
        durationInFrames={WINTER_QUESTION_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{ overlay: true }}
      />

      <Composition
        id="VaubanOverlay"
        component={VaubanOverlay}
        durationInFrames={OVERLAY_DURATION}
        fps={FPS}
        width={1080}
        height={1920}
      />

      <Composition
        // You can take the "id" to render a video:
        // npx remotion render HelloWorld
        id="HelloWorld"
        component={HelloWorld}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
        // You can override these props for each render:
        // https://www.remotion.dev/docs/parametrized-rendering
        schema={myCompSchema}
        defaultProps={{
          titleText: "Welcome to Remotion",
          titleColor: "#000000",
          logoColor1: "#91EAE4",
          logoColor2: "#86A8E7",
        }}
      />

      {/* Mount any React component to make it show up in the sidebar and work on it individually! */}
      <Composition
        id="OnlyLogo"
        component={Logo}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
        schema={myCompSchema2}
        defaultProps={{
          logoColor1: "#91dAE2" as const,
          logoColor2: "#86A8E7" as const,
        }}
      />
    </>
  );
};
