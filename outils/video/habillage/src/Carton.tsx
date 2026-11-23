import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {COULEURS, FILET, TEXTE, TITRAGE, echelle} from './charte';

/**
 * Le carton d'ouverture. Ce que le spectateur doit voir d'abord est le titre de la seance : tout le reste
 * est plus petit, plus pale, et arrive apres.
 *
 * Marges de securite : 80 px de cote et 100 px en haut et en bas pour 1080 de haut, mises a l'echelle.
 * En deca, un lecteur qui recadre mange le texte.
 */
export const Carton: React.FC<{titre: string; parcours: string; mention: string}> = ({
  titre,
  parcours,
  mention,
}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const e = echelle(height);

  // Une seule montee, sans rebond : un carton de cours n'est pas une bande-annonce.
  const paru = interpolate(frame, [0, fps * 0.5], [0, 1], {extrapolateRight: 'clamp'});
  const monte = interpolate(paru, [0, 1], [24 * e, 0]);
  const parutionTardive = interpolate(frame, [fps * 0.35, fps * 0.9], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COULEURS.marine,
        justifyContent: 'center',
        padding: `${100 * e}px ${80 * e}px`,
        fontFamily: TITRAGE,
      }}
    >
      <div style={{opacity: parutionTardive}}>
        <div
          style={{
            fontFamily: TEXTE,
            fontSize: 44 * e,
            letterSpacing: 2 * e,
            textTransform: 'uppercase',
            color: COULEURS.orangeClair,
          }}
        >
          {parcours}
        </div>
      </div>

      <div
        style={{
          opacity: paru,
          transform: `translateY(${monte}px)`,
          fontSize: 120 * e,
          fontWeight: 800,
          lineHeight: 1.05,
          color: '#ffffff',
          margin: `${28 * e}px 0`,
          maxWidth: '82%',
        }}
      >
        {titre}
      </div>

      <div style={{opacity: parutionTardive}}>
        <div style={{height: 10 * e, width: 420 * e, background: FILET, borderRadius: 999}} />
        <div
          style={{
            fontFamily: TEXTE,
            fontSize: 44 * e,
            color: COULEURS.ivoire,
            marginTop: 24 * e,
          }}
        >
          {mention}
        </div>
      </div>
    </AbsoluteFill>
  );
};
