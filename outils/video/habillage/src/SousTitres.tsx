import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {Replique} from './Seance';
import {TEXTE, echelle} from './charte';

/**
 * Les sous-titres incrustes.
 *
 * Les bornes des repliques comptent depuis le debut de la **seance**, pas du rendu : cette composition est
 * deja placee apres le carton par une `Sequence`, donc `useCurrentFrame` y repart de zero. Confondre les
 * deux decalerait tout le texte de la duree du carton — une faute invisible sur les premieres secondes et
 * flagrante a la fin.
 *
 * Ecrits en blanc sur un fond sombre translucide, et non en blanc borde de noir : une demonstration montre
 * souvent un terminal clair ou un editeur blanc, ou un bord noir ne suffit pas.
 */
export const SousTitres: React.FC<{repliques: Replique[]}> = ({repliques}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const e = echelle(height);
  const seconde = frame / fps;

  const courante = repliques.find((r) => seconde >= r.debut && seconde < r.fin);
  if (!courante) {
    return null;
  }

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-end',
        alignItems: 'center',
        padding: `0 ${120 * e}px ${64 * e}px`,
      }}
    >
      <div
        style={{
          fontFamily: TEXTE,
          fontSize: 48 * e,
          lineHeight: 1.3,
          fontWeight: 600,
          color: '#ffffff',
          textAlign: 'center',
          backgroundColor: 'rgba(0, 19, 46, 0.78)',
          padding: `${14 * e}px ${28 * e}px`,
          borderRadius: 12 * e,
          maxWidth: '78%',
        }}
      >
        {courante.texte}
      </div>
    </AbsoluteFill>
  );
};
