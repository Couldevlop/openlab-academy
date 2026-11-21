import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {COULEURS, FILET, TEXTE, TITRAGE, echelle} from './charte';

/**
 * Le rappel pendant les premieres secondes : ou l'on est, et a quelle seance.
 *
 * Il entre, reste, puis sort. Un bandeau qui ne sort jamais finit par etre ignore.
 *
 * **En haut**, et c'est une correction : place en bas, il se faisait recouvrir par le pave de
 * sous-titres des la premiere replique — vu a l'image, sur un rendu reel, et invisible pour tout test.
 * Le bas de l'ecran appartient aux sous-titres, qui y restent du debut a la fin ; le bandeau, lui, passe.
 */
export const Bandeau: React.FC<{parcours: string; mention: string}> = ({parcours, mention}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames, height} = useVideoConfig();
  const e = echelle(height);

  const entre = interpolate(frame, [0, fps * 0.4], [0, 1], {extrapolateRight: 'clamp'});
  const sort = interpolate(frame, [durationInFrames - fps * 0.4, durationInFrames], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const presence = Math.min(entre, sort);

  return (
    <AbsoluteFill style={{justifyContent: 'flex-start', padding: `${100 * e}px ${80 * e}px`}}>
      <div
        style={{
          opacity: presence,
          transform: `translateX(${interpolate(presence, [0, 1], [-40 * e, 0])}px)`,
          display: 'inline-flex',
          alignItems: 'stretch',
          alignSelf: 'flex-start',
          backgroundColor: 'rgba(0, 19, 46, 0.86)',
          borderRadius: 14 * e,
          overflow: 'hidden',
        }}
      >
        <div style={{width: 10 * e, background: FILET}} />
        <div style={{padding: `${20 * e}px ${32 * e}px`}}>
          <div
            style={{
              fontFamily: TITRAGE,
              fontSize: 46 * e,
              fontWeight: 700,
              color: '#ffffff',
            }}
          >
            {mention}
          </div>
          <div style={{fontFamily: TEXTE, fontSize: 34 * e, color: COULEURS.orangeClair}}>
            {parcours}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
