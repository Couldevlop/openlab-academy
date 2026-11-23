import {CalculateMetadataFunction, Composition} from 'remotion';
import {DUREE_CARTON_S, DUREE_PLAQUE_S, Seance, SeanceProps} from './Seance';

export const FPS = 30;
export const LARGEUR = 1920;
export const HAUTEUR = 1080;

/**
 * La duree du rendu vient de la seance, que le script Python a deja mesuree.
 *
 * On ne sonde pas la video ici : il faudrait soit un navigateur qui ouvre un fichier local, soit `ffprobe`
 * relance par Node. Les deux marchent un jour sur deux. `habiller.py` lit l'en-tete avec le meme ffmpeg qui
 * a produit le fichier, et passe la valeur. Si elle manque, on refuse plutot que de rendre une video
 * tronquee a la duree par defaut — personne ne regarde un rendu jusqu'au bout avant de le publier.
 */
const calculateMetadata: CalculateMetadataFunction<SeanceProps> = ({props}) => {
  if (!props.dureeVideo || props.dureeVideo <= 0) {
    throw new Error(
      'dureeVideo manquante ou nulle : lancez habiller.py, qui la mesure, plutot que remotion render a la main',
    );
  }
  const total = DUREE_CARTON_S + props.dureeVideo + DUREE_PLAQUE_S;
  return {durationInFrames: Math.ceil(total * FPS), fps: FPS};
};

export const Racine: React.FC = () => (
  <Composition
    id="seance"
    component={Seance}
    durationInFrames={FPS * 10}
    fps={FPS}
    width={LARGEUR}
    height={HAUTEUR}
    calculateMetadata={calculateMetadata}
    defaultProps={
      {
        video: '',
        dureeVideo: 10,
        titre: 'Titre de la seance',
        parcours: 'Nom du parcours',
        seance: 1,
        nature: 'intro',
        numeroDemo: 0,
        mention: 'Seance 01 · Introduction',
        sousTitres: [],
      } satisfies SeanceProps
    }
  />
);
