import {AbsoluteFill, OffthreadVideo, Sequence, staticFile, useVideoConfig} from 'remotion';
import {Bandeau} from './Bandeau';
import {Carton} from './Carton';
import {COULEURS} from './charte';
import {Plaque} from './Plaque';
import {SousTitres} from './SousTitres';

export const DUREE_CARTON_S = 2.5;
export const DUREE_PLAQUE_S = 2.5;
/** Le bandeau se retire une fois la seance lancee : il rappelle ou l'on est, il n'habite pas l'ecran. */
export const DUREE_BANDEAU_S = 4;

export type Replique = {
  debut: number;
  fin: number;
  texte: string;
};

export type SeanceProps = {
  /**
   * Nom du fichier de la seance, et rien de plus.
   *
   * Le dossier qui le contient est passe au rendu comme dossier public (`--public-dir`), et `staticFile`
   * l'y retrouve. Un chemin de disque ne marcherait pas : Remotion telecharge les ressources d'une
   * composition, et une URL `file:` echoue a la lecture.
   */
  video: string;
  dureeVideo: number;
  titre: string;
  parcours: string;
  seance: number;
  nature: string;
  numeroDemo: number;
  mention: string;
  /** Sous-titres deja analyses, en secondes depuis le debut de la seance (et non du rendu). */
  sousTitres: Replique[];
};

export const Seance: React.FC<SeanceProps> = ({
  video,
  dureeVideo,
  titre,
  parcours,
  mention,
  sousTitres,
}) => {
  const {fps} = useVideoConfig();
  const carton = Math.round(DUREE_CARTON_S * fps);
  const corps = Math.round(dureeVideo * fps);

  return (
    <AbsoluteFill style={{backgroundColor: COULEURS.nuit}}>
      <Sequence durationInFrames={carton}>
        <Carton titre={titre} parcours={parcours} mention={mention} />
      </Sequence>

      <Sequence from={carton} durationInFrames={corps}>
        {video ? (
          <OffthreadVideo src={staticFile(video)} />
        ) : (
          // Dans le Studio, sans propriete : un fond plutot qu'un ecran noir qu'on prend pour une panne.
          <AbsoluteFill style={{backgroundColor: COULEURS.marine}} />
        )}
        <Sequence durationInFrames={Math.round(DUREE_BANDEAU_S * fps)}>
          <Bandeau parcours={parcours} mention={mention} />
        </Sequence>
        <SousTitres repliques={sousTitres} />
      </Sequence>

      <Sequence from={carton + corps}>
        <Plaque parcours={parcours} />
      </Sequence>
    </AbsoluteFill>
  );
};
