import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {COULEURS, FILET, TEXTE, TITRAGE, echelle} from './charte';

/**
 * La plaque de fin. Elle ne dit qu'une chose : la suite se passe dans le parcours.
 *
 * Pas d'adresse ecrite en dur, pas de « abonnez-vous » : la video est servie depuis la seance elle-meme,
 * et l'apprenant qui la regarde est deja inscrit. Une incitation ici vieillirait plus vite que le cours.
 */
export const Plaque: React.FC<{parcours: string}> = ({parcours}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const e = echelle(height);
  const paru = interpolate(frame, [0, fps * 0.45], [0, 1], {extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COULEURS.marine,
        justifyContent: 'center',
        alignItems: 'center',
        padding: `${100 * e}px ${80 * e}px`,
        opacity: paru,
      }}
    >
      <div style={{height: 10 * e, width: 360 * e, background: FILET, borderRadius: 999}} />
      <div
        style={{
          fontFamily: TITRAGE,
          fontSize: 84 * e,
          fontWeight: 800,
          color: '#ffffff',
          marginTop: 36 * e,
          textAlign: 'center',
        }}
      >
        La suite dans votre parcours
      </div>
      <div
        style={{
          fontFamily: TEXTE,
          fontSize: 44 * e,
          color: COULEURS.orangeClair,
          marginTop: 20 * e,
          textAlign: 'center',
        }}
      >
        {parcours}
      </div>
    </AbsoluteFill>
  );
};
