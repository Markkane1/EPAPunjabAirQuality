import { renderToStaticMarkup } from 'react-dom/server';
import type { WorkstationModel } from './state';
import { renderWorkstation } from './WorkstationView';

export function renderModel(model: WorkstationModel): string {
  return renderToStaticMarkup(renderWorkstation(model));
}
