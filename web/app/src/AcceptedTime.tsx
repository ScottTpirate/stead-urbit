export function AcceptedTime({milliseconds}: {milliseconds: string}) {
  if (!/^[1-9][0-9]{0,19}$/u.test(milliseconds) || BigInt(milliseconds) > 8640000000000000n) {
    return <span>Time unavailable</span>;
  }
  const date = new Date(Number(milliseconds));
  const iso = date.toISOString();
  const display = new Intl.DateTimeFormat(undefined, {year: 'numeric', month: 'short', day: 'numeric',
    hour: 'numeric', minute: '2-digit', timeZoneName: 'short'}).format(date);
  return <time dateTime={iso} title={iso}>{display}</time>;
}
