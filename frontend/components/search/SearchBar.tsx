'use client';

import { useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, X, Cpu, AlignLeft, Layers } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { SearchMode } from '@/lib/types';

// ─── Mode Toggle ─────────────────────────────────────────────

const MODES: { value: SearchMode; label: string; icon: React.ElementType; description: string }[] = [
  {
    value: 'keyword',
    label: 'Keyword',
    icon: AlignLeft,
    description: 'Exact term matching',
  },
  {
    value: 'semantic',
    label: 'Semantic',
    icon: Cpu,
    description: 'AI meaning search',
  },
  {
    value: 'hybrid',
    label: 'Hybrid',
    icon: Layers,
    description: 'Combined approach',
  },
];

// ─── Props ───────────────────────────────────────────────────

export interface SearchBarProps {
  value?: string;
  mode?: SearchMode;
  placeholder?: string;
  autoFocus?: boolean;
  onSearch?: (query: string, mode: SearchMode) => void;
  onChange?: (query: string) => void;
  onModeChange?: (mode: SearchMode) => void;
  className?: string;
  showModeSelector?: boolean;
}

// ─── Component ───────────────────────────────────────────────

export function SearchBar({
  value: externalValue,
  mode: externalMode = 'hybrid',
  placeholder = 'Search intelligence, signals, trends…',
  autoFocus = false,
  onSearch,
  onChange,
  onModeChange,
  className,
  showModeSelector = true,
}: SearchBarProps) {
  const [internalQuery, setInternalQuery] = useState(externalValue ?? '');
  const [internalMode, setInternalMode] = useState<SearchMode>(externalMode);
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const query = externalValue !== undefined ? externalValue : internalQuery;
  const mode = internalMode;

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const v = e.target.value;
      if (externalValue === undefined) setInternalQuery(v);
      onChange?.(v);
    },
    [externalValue, onChange]
  );

  const handleClear = useCallback(() => {
    if (externalValue === undefined) setInternalQuery('');
    onChange?.('');
    inputRef.current?.focus();
  }, [externalValue, onChange]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' && query.trim()) {
        onSearch?.(query.trim(), mode);
      }
    },
    [query, mode, onSearch]
  );

  const handleModeChange = useCallback(
    (newMode: SearchMode) => {
      setInternalMode(newMode);
      onModeChange?.(newMode);
    },
    [onModeChange]
  );

  return (
    <div className={cn('flex flex-col gap-3', className)}>
      {/* Search input */}
      <motion.div
        animate={{
          borderColor: isFocused
            ? 'rgba(99,102,241,0.6)'
            : 'rgba(33,38,45,1)',
          boxShadow: isFocused
            ? '0 0 0 3px rgba(99,102,241,0.12)'
            : '0 0 0 0px transparent',
        }}
        transition={{ duration: 0.15 }}
        className="flex items-center gap-3 rounded-lg border bg-surface-elevated px-4 py-3"
      >
        <Search
          className={cn(
            'h-4 w-4 shrink-0 transition-colors duration-150',
            isFocused ? 'text-brand-400' : 'text-muted-foreground'
          )}
        />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder={placeholder}
          autoFocus={autoFocus}
          className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground/60 outline-none"
        />
        <AnimatePresence>
          {query && (
            <motion.button
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.1 }}
              onClick={handleClear}
              className="flex h-5 w-5 items-center justify-center rounded-full bg-surface-muted text-muted-foreground hover:bg-surface-border hover:text-foreground transition-colors"
            >
              <X className="h-3 w-3" />
            </motion.button>
          )}
        </AnimatePresence>
        {query.trim() && (
          <button
            onClick={() => onSearch?.(query.trim(), mode)}
            className="shrink-0 rounded-md bg-brand-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-600 transition-colors"
          >
            Search
          </button>
        )}
      </motion.div>

      {/* Mode selector */}
      {showModeSelector && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Mode:</span>
          <div className="flex rounded-md border border-surface-border bg-surface-elevated p-0.5 gap-0.5">
            {MODES.map(({ value, label, icon: Icon, description }) => (
              <button
                key={value}
                onClick={() => handleModeChange(value)}
                title={description}
                className={cn(
                  'flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-medium transition-all duration-150',
                  mode === value
                    ? 'bg-brand-500 text-white shadow-sm'
                    : 'text-muted-foreground hover:text-foreground hover:bg-surface-muted'
                )}
              >
                <Icon className="h-3 w-3" />
                {label}
              </button>
            ))}
          </div>
          <span className="text-[10px] text-muted-foreground">
            {MODES.find((m) => m.value === mode)?.description}
          </span>
        </div>
      )}
    </div>
  );
}
