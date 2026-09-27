import {Button} from './primitives';
import {supportDetails} from './support';
export function SupportDetails({code, requestId}: {code: string; requestId?: string}) {
  const details = supportDetails(code, requestId);
  function download() {
    const url = URL.createObjectURL(new Blob([details], {type: 'application/json'}));
    const link = document.createElement('a'); link.href = url; link.download = 'stead-support.json';
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <details className="support"><summary>Support details</summary>
    <p>Review these details before downloading. They contain app versions, a diagnostic code and, when a save is pending, its request ID. They exclude cookies, keys, names, messages and document contents. Nothing is sent automatically.</p>
    <pre aria-label="Support report preview">{details}</pre>
    <Button onClick={download}>Download these details</Button>
  </details>;
}
