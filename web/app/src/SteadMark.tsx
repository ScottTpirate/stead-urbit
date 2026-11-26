import {sectionPaths, steadPaths} from './brandGeometry';
import './brand.css';

export function SteadMark({section}: {section?: keyof typeof sectionPaths}) {
  const paths = section ? sectionPaths[section] : steadPaths;
  return <svg
    className={section ? 'stead-section-mark' : 'stead-brand-mark'}
    viewBox={section ? '0 0 16 16' : '0 0 1 1'}
    fill="currentColor" aria-hidden="true" focusable="false"
  >{paths.map(path => <path key={path} d={path}/>)}</svg>;
}
