@props(['tone' => 'slate'])

@php
    $colors = [
        'green' => 'bg-emerald-100 text-emerald-800',
        'amber' => 'bg-amber-100 text-amber-800',
        'red' => 'bg-red-100 text-red-800',
        'violet' => 'bg-marca-50 text-marca-800 ring-1 ring-marca-200',
        'slate' => 'bg-slate-200 text-slate-700',
    ][$tone] ?? 'bg-slate-200 text-slate-700';
@endphp

<span {{ $attributes->class(['inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold whitespace-nowrap', $colors]) }}>{{ $slot }}</span>
