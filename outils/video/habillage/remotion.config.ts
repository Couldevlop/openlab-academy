import {Config} from '@remotion/cli/config';

// H.264 en qualite de diffusion : les seances sont servies en flux par le site, pas archivees.
Config.setVideoImageFormat('jpeg');
Config.setCodec('h264');
Config.setCrf(20);
// Le rendu lit un fichier local (file://) : sans cela Chrome refuse la video de la seance.
Config.setChromiumOpenGlRenderer('angle');
