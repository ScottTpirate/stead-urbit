import {
  default as React,
  forwardRef,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type RefObject,
} from "react";
import { createPortal } from "react-dom";
import {Icon} from './Icon';
import './controls.css';

function joinClassNames(
  ...classNames: Array<string | false | null | undefined>
): string {
  return classNames.filter(Boolean).join(" ");
}

const FORBIDDEN_FORWARDED_DOM_PROPERTIES = new Set([
  "action",
  "background",
  "backgroundimage",
  "codebase",
  "csstext",
  "dangerouslysetinnerhtml",
  "data",
  "formaction",
  "href",
  "innerhtml",
  "outerhtml",
  "ping",
  "poster",
  "src",
  "srcdoc",
  "srcset",
  "style",
]);

function governedDomProperties<TProperties extends object>(
  properties: TProperties,
): TProperties {
  for (const name of Reflect.ownKeys(properties)) {
    if (
      typeof name !== "string" ||
      FORBIDDEN_FORWARDED_DOM_PROPERTIES.has(name.toLowerCase())
    ) {
      throw new Error("resource-loading DOM properties are not supported");
    }
  }
  return properties;
}

export type ButtonVariant = "primary" | "secondary" | "quiet" | "danger";

export interface ButtonProps
  extends Omit<
    ButtonHTMLAttributes<HTMLButtonElement>,
    "dangerouslySetInnerHTML" | "formAction" | "style"
  > {
  readonly variant?: ButtonVariant;
  readonly pending?: boolean;
  readonly pendingLabel?: string;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    className,
    variant = "secondary",
    pending = false,
    pendingLabel = "Working",
    disabled,
    children,
    type = "button",
    ...properties
  },
  reference,
) {
  return (
    <button
      {...governedDomProperties(properties)}
      ref={reference}
      className={joinClassNames("stead-button", `stead-button--${variant}`, className)}
      type={type}
      disabled={disabled || pending}
      aria-busy={pending || undefined}
    >
      {pending ? <span className="stead-spinner" aria-hidden="true" /> : null}
      <span>{pending ? pendingLabel : children}</span>
    </button>
  );
});

export interface TextFieldProps
  extends Omit<
    InputHTMLAttributes<HTMLInputElement>,
    "dangerouslySetInnerHTML" | "formAction" | "src" | "style"
  > {
  readonly label: string;
  readonly description?: string;
  readonly error?: string;
}

export const TextField = forwardRef<HTMLInputElement, TextFieldProps>(
  function TextField(
    { className, id, label, description, error, ...properties },
    reference,
  ) {
    const generatedId = useId();
    const inputId = id ?? generatedId;
    const descriptionId = description ? `${inputId}-description` : undefined;
    const errorId = error ? `${inputId}-error` : undefined;
    const describedBy = [descriptionId, errorId].filter(Boolean).join(" ") || undefined;
    return (
      <div className="stead-field">
        <label className="stead-field__label" htmlFor={inputId}>
          {label}
        </label>
        {description ? (
          <span className="stead-field__description" id={descriptionId}>
            {description}
          </span>
        ) : null}
        <input
          {...governedDomProperties(properties)}
          ref={reference}
          id={inputId}
          className={joinClassNames("stead-field__control", className)}
          aria-describedby={describedBy}
          aria-invalid={error ? true : undefined}
        />
        {error ? (
          <span className="stead-field__error" id={errorId} role="alert">
            {error}
          </span>
        ) : null}
      </div>
    );
  },
);

export interface SurfaceProps
  extends Omit<HTMLAttributes<HTMLElement>, "dangerouslySetInnerHTML" | "style"> {
  readonly children: ReactNode;
  readonly elevated?: boolean;
}

export function Surface({
  children,
  className,
  elevated = false,
  ...properties
}: SurfaceProps) {
  return (
    <section
      {...governedDomProperties(properties)}
      className={joinClassNames(
        "stead-surface",
        elevated && "stead-surface--elevated",
        className,
      )}
    >
      {children}
    </section>
  );
}

export interface EmptyStateProps {
  readonly title: string;
  readonly description: string;
  readonly action?: ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="stead-state" data-state="empty">
      <span className="stead-state__glyph" aria-hidden="true">
        ◌
      </span>
      <h2>{title}</h2>
      <p>{description}</p>
      {action ? <div className="stead-state__action">{action}</div> : null}
    </div>
  );
}

export interface LoadingStateProps {
  readonly label?: string;
  readonly lines?: number;
}

export function LoadingState({
  label = "Loading authorized content",
  lines = 3,
}: LoadingStateProps) {
  return (
    <div className="stead-state stead-state--loading" data-state="loading" aria-busy="true">
      <span className="stead-visually-hidden" role="status">
        {label}
      </span>
      <div aria-hidden="true" className="stead-skeleton" data-lines={lines}>
        {Array.from({ length: lines }, (_, index) => (
          <span key={index} />
        ))}
      </div>
    </div>
  );
}

export interface ErrorStateProps {
  readonly title?: string;
  readonly correlationId?: string;
  readonly onRetry?: () => void;
}

const SAFE_CORRELATION_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/u;

function safeCorrelationId(value: unknown): string | undefined {
  return typeof value === "string" && SAFE_CORRELATION_ID_PATTERN.test(value)
    ? value
    : undefined;
}

export function ErrorState({
  title = "This view is unavailable",
  correlationId,
  onRetry,
}: ErrorStateProps) {
  const visibleCorrelationId = safeCorrelationId(correlationId);
  return (
    <div className="stead-state" data-state="error" role="alert">
      <span className="stead-state__glyph stead-state__glyph--error" aria-hidden="true">
        !
      </span>
      <h2>{title}</h2>
      <p>Try again. If the problem continues, share the correlation ID with an administrator.</p>
      {visibleCorrelationId ? <code>{visibleCorrelationId}</code> : null}
      {onRetry ? (
        <div className="stead-state__action">
          <Button onClick={onRetry}>Try again</Button>
        </div>
      ) : null}
    </div>
  );
}

export interface SecurityMarkingProps {
  readonly label: string;
  readonly markings: readonly { readonly kind: string; readonly text: string }[];
}

export function SecurityMarking({ label, markings }: SecurityMarkingProps) {
  return (
    <aside className="stead-security-marking" aria-label={label}>
      <span className="stead-security-marking__label">{label}</span>
      {markings.map((marking, index) => (
        <span key={`${marking.kind}-${index}`} data-marking-kind={marking.kind}>
          {marking.text}
        </span>
      ))}
    </aside>
  );
}

// Coordinates are computed from our own trigger and viewport. Callers cannot
// forward style, URLs, raw HTML or other resource-loading DOM properties here.
function useControlPopup(open: boolean, close: (restoreFocus?: boolean) => void) {
  const trigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const closeRef = useRef(close);
  closeRef.current = close;
  useLayoutEffect(() => {
    if (!open) return;
    function position() {
      const button = trigger.current;
      const popup = panel.current;
      if (!button || !popup) return;
      const rect = button.getBoundingClientRect();
      const left = Math.max(8, Math.min(rect.left, window.innerWidth - popup.offsetWidth - 8));
      const below = rect.bottom + 6;
      const top = below + popup.offsetHeight <= window.innerHeight - 8 ? below
        : Math.max(8, rect.top - popup.offsetHeight - 6);
      popup.style.left = `${left}px`;
      popup.style.top = `${top}px`;
    }
    position();
    const observer = new ResizeObserver(position);
    if (panel.current) observer.observe(panel.current);
    window.addEventListener('resize', position);
    window.addEventListener('scroll', position, true);
    return () => {
      observer.disconnect();
      window.removeEventListener('resize', position);
      window.removeEventListener('scroll', position, true);
    };
  }, [open]);
  useEffect(() => {
    if (!open) return;
    function outside(event: Event) {
      if (event.target instanceof Node && !panel.current?.contains(event.target)
          && !trigger.current?.contains(event.target)) closeRef.current(false);
    }
    document.addEventListener('pointerdown', outside);
    document.addEventListener('focusin', outside);
    return () => {
      document.removeEventListener('pointerdown', outside);
      document.removeEventListener('focusin', outside);
    };
  }, [open]);
  return { trigger, panel };
}

export interface MenuItem {
  readonly value: string;
  readonly label: string;
  readonly onSelect: () => void;
  readonly checked?: boolean;
  readonly disabled?: boolean;
  readonly danger?: boolean;
}

export interface MenuProps {
  readonly label: string;
  readonly triggerLabel?: ReactNode;
  readonly items: readonly MenuItem[];
  readonly disabled?: boolean;
}

/** An action menu. Selection controls use checked items; never untrusted HTML. */
export function Menu({ label, triggerLabel, items, disabled = false }: MenuProps) {
  const [open, setOpen] = useState(false);
  const [initial, setInitial] = useState<'first' | 'last' | 'selected'>('selected');
  const id = useId();
  const search = useRef({ text: '', time: 0 });
  const close = (restoreFocus = true) => {
    setOpen(false);
    if (restoreFocus) trigger.current?.focus();
  };
  const { trigger, panel } = useControlPopup(open, close);
  useLayoutEffect(() => {
    if (!open) return;
    const buttons = [...(panel.current?.querySelectorAll<HTMLButtonElement>('button:enabled') ?? [])];
    const selected = initial === 'last' ? buttons.at(-1)
      : initial === 'selected' ? buttons.find(button => button.getAttribute('aria-checked') === 'true') ?? buttons[0]
      : buttons[0];
    (selected ?? panel.current)?.focus();
  }, [open, initial]);
  useEffect(() => { if (disabled) setOpen(false); }, [disabled]);
  return <>
    <Button ref={trigger} variant="quiet" disabled={disabled} aria-label={label}
      aria-haspopup="menu" aria-expanded={open} aria-controls={open ? id : undefined}
      onClick={() => { setInitial('selected'); setOpen(value => !value); }}
      onKeyDown={event => {
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
          event.preventDefault(); setInitial(event.key === 'ArrowUp' ? 'last' : 'first'); setOpen(true);
        }
      }}>{triggerLabel ?? label}<span className="stead-picker-chevron"><Icon name="chevron-down"/></span></Button>
    {open && createPortal(<div ref={panel} id={id} className="stead-control-popup" role="menu" aria-label={label} tabIndex={-1}
      onKeyDown={event => {
        if (event.key === 'Escape' || event.key === 'Tab') {
          if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); }
          close(); return;
        }
        const buttons = [...(panel.current?.querySelectorAll<HTMLButtonElement>('button:enabled') ?? [])];
        if (!buttons.length) return;
        const index = buttons.findIndex(button => button === document.activeElement);
        if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
          event.preventDefault();
          const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1
            : event.key === 'ArrowDown' ? (index + 1) % buttons.length
              : (index - 1 + buttons.length) % buttons.length;
          buttons[next]?.focus();
        } else if (event.key.length === 1 && event.key !== ' ' && !event.ctrlKey && !event.metaKey && !event.altKey) {
          const now = Date.now();
          search.current = { text: (now - search.current.time < 600 ? search.current.text : '') + event.key.toLocaleLowerCase(), time: now };
          const text = search.current.text;
          const next = [...buttons.slice(index + 1), ...buttons.slice(0, index + 1)]
            .find(button => button.textContent?.trim().toLocaleLowerCase().startsWith(text));
          if (next) { event.preventDefault(); next.focus(); }
        }
      }}>
      {items.map(item => <button key={item.value} type="button" tabIndex={-1}
        role={item.checked === undefined ? 'menuitem' : 'menuitemradio'} aria-checked={item.checked}
        disabled={item.disabled} className={item.danger ? 'stead-control-option stead-control-option--danger' : 'stead-control-option'}
        onClick={() => { close(); item.onSelect(); }}>
        <span>{item.label}</span>{item.checked && <span className="stead-control-check"><Icon name="check"/></span>}
      </button>)}
      {!items.length && <p className="stead-control-note">No actions available</p>}
    </div>, trigger.current?.closest('dialog[open]') ?? document.body)}
  </>;
}

export interface PickerOption {
  readonly value: string;
  readonly label: string;
  readonly description?: string;
  readonly disabled?: boolean;
  readonly kind?: 'human' | 'agent';
}

export interface ComboboxProps {
  readonly label: string;
  readonly value: string;
  readonly options: readonly PickerOption[];
  readonly onChange: (value: string) => void;
  readonly placeholder?: string;
  readonly disabled?: boolean;
  readonly loading?: boolean;
  readonly error?: string;
  readonly onRetry?: () => void;
}

/** Search retains DOM focus in the input; listbox focus is aria-activedescendant. */
export function Combobox({ label, value, options, onChange, placeholder = 'Choose…', disabled = false,
  loading = false, error, onRetry }: ComboboxProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [active, setActive] = useState('');
  const input = useRef<HTMLInputElement>(null);
  const id = useId();
  const close = (restoreFocus = true) => {
    setOpen(false); setQuery('');
    if (restoreFocus) trigger.current?.focus();
  };
  const { trigger, panel } = useControlPopup(open, close);
  const selected = options.find(option => option.value === value);
  const term = query.trim().toLocaleLowerCase();
  const filtered = loading || error ? [] : options.filter(option => `${option.label} ${option.description ?? ''}`.toLocaleLowerCase().includes(term));
  const enabled = filtered.filter(option => !option.disabled);
  const activeValue = enabled.some(option => option.value === active) ? active : enabled[0]?.value;
  const activeIndex = filtered.findIndex(option => option.value === activeValue);
  useLayoutEffect(() => { if (open) input.current?.focus(); }, [open]);
  useEffect(() => { if (disabled) setOpen(false); }, [disabled]);
  useEffect(() => {
    if (open && activeIndex >= 0) document.getElementById(`${id}-option-${activeIndex}`)?.scrollIntoView({block: 'nearest'});
  }, [open, id, activeIndex]);
  function choose(option: PickerOption) {
    if (option.disabled || loading || error) return;
    close(); onChange(option.value);
  }
  return <>
    <Button ref={trigger} variant="quiet" disabled={disabled} aria-label={`${label}: ${selected?.label ?? placeholder}`}
      aria-haspopup="dialog" aria-expanded={open} aria-controls={open ? `${id}-popup` : undefined}
      onClick={() => { setActive(value); setOpen(current => !current); }}
      onKeyDown={event => {
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); setActive(value); setOpen(true); }
      }}><span className="stead-picker-label">{label}</span><span className="stead-picker-value">{selected?.label ?? placeholder}</span>
      <span className="stead-picker-chevron"><Icon name="chevron-down"/></span></Button>
    {open && createPortal(<div ref={panel} id={`${id}-popup`} className="stead-control-popup stead-combobox" role="dialog" aria-label={`Choose ${label.toLocaleLowerCase()}`}
      onKeyDown={event => {
        if (event.key === 'Escape' || event.key === 'Tab') {
          if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); }
          close();
        }
      }}>
      <label className="stead-visually-hidden" htmlFor={`${id}-search`}>Search {label.toLocaleLowerCase()}</label>
      <input ref={input} id={`${id}-search`} role="combobox" aria-autocomplete="list" aria-expanded="true"
        aria-controls={`${id}-options`} aria-activedescendant={activeIndex >= 0 ? `${id}-option-${activeIndex}` : undefined}
        placeholder={`Search ${label.toLocaleLowerCase()}…`} value={query}
        onChange={event => { setQuery(event.target.value); setActive(''); }}
        onKeyDown={event => {
          if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
            event.preventDefault();
            const index = enabled.findIndex(option => option.value === activeValue);
            const next = event.key === 'ArrowDown' ? (index + 1) % enabled.length : (index - 1 + enabled.length) % enabled.length;
            const option = enabled[next]; if (option) setActive(option.value);
          } else if (event.key === 'Enter') {
            event.preventDefault(); const option = enabled.find(candidate => candidate.value === activeValue); if (option) choose(option);
          }
        }}/>
      <div role="listbox" id={`${id}-options`} aria-label={label} aria-busy={loading || undefined}>
        {filtered.map((option, index) => <div key={option.value} id={`${id}-option-${index}`} role="option"
          aria-selected={option.value === value} aria-disabled={option.disabled || undefined}
          data-active={option.value === activeValue ? 'true' : undefined} className="stead-control-option"
          onPointerMove={() => { if (!option.disabled) setActive(option.value); }}
          onPointerDown={event => event.preventDefault()} onClick={() => choose(option)}>
          <span>{option.label}{option.description && <small>{option.description}</small>}</span>
          {option.kind === 'agent' && <span className="stead-person-kind">Agent</span>}
          {option.value === value && <span className="stead-control-check"><Icon name="check"/></span>}
        </div>)}
      </div>
      {loading ? <p className="stead-control-note" role="status">Loading options…</p>
        : error ? <div className="stead-control-note" role="alert"><p>{error}</p>{onRetry && <Button onClick={onRetry}>Try again</Button>}</div>
          : !filtered.length ? <p className="stead-control-note" role="status">{term ? 'No matching options' : 'No eligible options'}</p> : null}
    </div>, trigger.current?.closest('dialog[open]') ?? document.body)}
  </>;
}

export interface PropertyPickerProps extends ComboboxProps { readonly searchable?: boolean }

export function PropertyPicker({ searchable = false, ...props }: PropertyPickerProps) {
  if (searchable) return <Combobox {...props}/>;
  const selected = props.options.find(option => option.value === props.value);
  const display = selected?.label ?? props.placeholder ?? 'Choose…';
  return <Menu label={`${props.label}: ${display}`} disabled={props.disabled || props.loading || !!props.error}
    triggerLabel={<><span className="stead-picker-label">{props.label}</span><span className="stead-picker-value">{display}</span></>}
    items={props.options.map(option => ({ value: option.value, label: option.label, checked: props.value === option.value,
      disabled: option.disabled, onSelect: () => props.onChange(option.value) }))}/>;
}

export interface DialogProps {
  readonly open: boolean;
  readonly title: string;
  readonly description?: string;
  readonly children: ReactNode;
  readonly footer?: ReactNode;
  readonly onClose: () => void;
  readonly initialFocus?: RefObject<HTMLElement | null>;
}

export function Dialog({ open, title, description, children, footer, onClose, initialFocus }: DialogProps) {
  const dialog = useRef<HTMLDialogElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);
  const id = useId();
  useLayoutEffect(() => {
    const node = dialog.current;
    if (!node) return;
    if (open && !node.open) {
      previousFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      node.showModal();
      (initialFocus?.current ?? node.querySelector<HTMLElement>('input:not(:disabled), textarea:not(:disabled), [data-dialog-initial-focus]') ?? node).focus();
    } else if (!open && node.open) {
      node.close();
      if (previousFocus.current?.isConnected) previousFocus.current.focus();
    }
  }, [open, initialFocus]);
  useEffect(() => () => {
    if (previousFocus.current?.isConnected) previousFocus.current.focus();
  }, []);
  return <dialog ref={dialog} className="stead-dialog" tabIndex={-1} aria-labelledby={`${id}-title`}
    aria-describedby={description ? `${id}-description` : undefined}
    onKeyDown={event => {
      if (event.key !== 'Tab' || event.defaultPrevented) return;
      const controls = [...(dialog.current?.querySelectorAll<HTMLElement>('button, input, textarea, select, a[href], [tabindex], [contenteditable="true"]') ?? [])]
        .filter(control => control.tabIndex >= 0 && !control.matches(':disabled') && control.getClientRects().length > 0);
      const first = controls[0], last = controls.at(-1);
      if (!first) { event.preventDefault(); dialog.current?.focus(); }
      else if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog.current)) {
        event.preventDefault(); last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first.focus();
      }
    }}
    onCancel={event => { event.preventDefault(); onClose(); }}>
    <header className="stead-dialog-header"><h2 id={`${id}-title`}>{title}</h2>
      <Button variant="quiet" aria-label={`Close ${title}`} onClick={onClose}>Close</Button></header>
    {description && <p id={`${id}-description`} className="stead-dialog-description">{description}</p>}
    <div className="stead-dialog-body">{children}</div>
    {footer && <footer className="stead-dialog-footer">{footer}</footer>}
  </dialog>;
}

export interface PersonBadgeProps {
  readonly name: string;
  readonly kind?: 'human' | 'agent';
  readonly inherited?: boolean;
}

export function PersonBadge({ name, kind = 'human', inherited = false }: PersonBadgeProps) {
  const initials = name.trim().split(/\s+/u).slice(0, 2).map(word => [...word][0] ?? '').join('').toLocaleUpperCase();
  return <span className="stead-person"><span className="stead-person-avatar" aria-hidden="true">{initials || '?'}</span>
    <span className="stead-person-name">{name || 'Unnamed participant'}</span>
    {kind === 'agent' && <span className="stead-person-kind">Agent</span>}
    {inherited && <span className="stead-person-inherited">Project steward</span>}</span>;
}

export function StatusBadge({ label, tone = 'neutral' }: { readonly label: string; readonly tone?: 'neutral' | 'active' | 'success' | 'warning' | 'danger' }) {
  return <span className="stead-status-badge" data-tone={tone}><Icon name={tone === 'success' ? 'check' : tone === 'warning' || tone === 'danger' ? 'circle-exclamation-point' : 'circle'}/>{label}</span>;
}

export type OutcomeStateKind = 'read_only' | 'dirty_draft' | 'saving' | 'accepted' | 'disconnected_or_stale'
  | 'outcome_unknown' | 'conflict' | 'permission_revoked' | 'retryable_error' | 'unsupported_operation';

const outcomeCopy: Record<OutcomeStateKind, { title: string; description: string }> = {
  read_only: { title: 'Read only', description: 'You can read this content, but cannot change it.' },
  dirty_draft: { title: 'Unsaved changes', description: 'Your changes have not been saved.' },
  saving: { title: 'Saving…', description: 'Waiting for this Home to confirm your changes.' },
  accepted: { title: 'Saved', description: 'This Home accepted your changes.' },
  disconnected_or_stale: { title: 'Connection interrupted', description: 'This view may be out of date. Reconnect before making changes.' },
  outcome_unknown: { title: 'Checking whether this saved…', description: 'Keep this draft while the original request is reconciled.' },
  conflict: { title: 'A newer version is available', description: 'Compare it with your draft before choosing what to save.' },
  permission_revoked: { title: 'Access has changed', description: 'This content is no longer available with your current access.' },
  retryable_error: { title: 'This action could not be completed', description: 'Try again when the connection is available.' },
  unsupported_operation: { title: 'Not available here', description: 'This configuration does not support this operation.' },
};

/** Callers supply an accepted state only after a durable native receipt. */
export function OutcomeState({ state, description, action }: { readonly state: OutcomeStateKind; readonly description?: string; readonly action?: ReactNode }) {
  const copy = outcomeCopy[state];
  const urgent = state === 'conflict' || state === 'permission_revoked' || state === 'retryable_error';
  return <div className="stead-outcome" data-state={state} role={urgent ? 'alert' : 'status'} aria-busy={state === 'saving' || state === 'outcome_unknown' || undefined}>
    <strong>{copy.title}</strong><p>{description ?? copy.description}</p>{action && <div className="stead-outcome-action">{action}</div>}
  </div>;
}
