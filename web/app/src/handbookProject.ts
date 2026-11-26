import {HomeClient, type ViewKind} from './api';
import {handbookDocs, handbookFetch, handbookProject} from './handbookData';
import type {HandbookPage, ProductRoute} from './productRoutes';

export const handbookClient = new HomeClient(handbookFetch);
let ready: Promise<void> | undefined;
export function prepareHandbook() {
  return ready ??= (async () => {
    await handbookClient.capabilities();
    await handbookClient.resume();
  })().catch(error => { ready = undefined; throw error; });
}

export function handbookDocument(page: HandbookPage) {
  if (Object.hasOwn(handbookDocs, page)) return handbookDocs[page as keyof typeof handbookDocs];
}

export function handbookTab(page: HandbookPage): ViewKind {
  if (page === 'docs' || handbookDocument(page)) return 'documents';
  if (page === 'work' || page === 'example') return 'work';
  if (page === 'activity' || page === 'relations' || page === 'search') return page;
  return 'project';
}

export function handbookAddress(route: ProductRoute): ProductRoute {
  if (!('project' in route) || route.project !== handbookProject.project_id) return route;
  let page: HandbookPage;
  switch (route.kind) {
    case 'project': page = route.view; break;
    case 'work': page = route.item ? 'example' : 'work'; break;
    case 'collection': page = 'docs'; break;
    case 'doc': {
      const key = (Object.keys(handbookDocs) as (keyof typeof handbookDocs)[])
        .find(slug => handbookDocs[slug].resource_id === route.document);
      page = key ?? 'docs';
      break;
    }
    default: return route;
  }
  return {kind: 'handbook', page};
}
