@extends('layouts.app')

@section('content')
    <div class="mb-5 grid grid-cols-3 gap-3">
        @foreach ([[$total, 'Suscriptores'], [$active, 'Activos'], [$total - $active, 'En pausa']] as [$n, $label])
            <div class="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
                <div class="text-2xl font-semibold text-marca-950">{{ $n }}</div>
                <div class="text-sm text-slate-500">{{ $label }}</div>
            </div>
        @endforeach
    </div>

    <div class="mb-4 flex flex-col gap-3 sm:flex-row">
        <form method="GET" class="flex-1">
            <input type="search" name="q" value="{{ $q }}" placeholder="Buscar por nombre, correo, región, palabra o entidad"
                   class="w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm focus:border-marca-600 focus:outline-none focus:ring-4 focus:ring-marca-100">
        </form>
        <a href="{{ route('subscribers.create') }}" class="rounded-xl bg-marca-700 px-4 py-2.5 text-center text-sm font-semibold text-white hover:bg-marca-800">+ Nuevo suscriptor</a>
    </div>

    @forelse ($subscribers as $s)
        <article class="mb-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm {{ $s->paused ? 'opacity-70' : '' }}">
            <div class="flex flex-wrap items-start gap-3">
                <div class="flex h-11 w-11 flex-none items-center justify-center rounded-xl bg-marca-700 font-semibold text-white">
                    {{ mb_strtoupper(mb_substr($s->name, 0, 2)) }}
                </div>
                <div class="min-w-0 flex-1">
                    <div class="flex flex-wrap items-center gap-2">
                        <a href="{{ route('subscribers.edit', $s) }}" class="font-semibold hover:text-marca-700">{{ $s->name }}</a>
                        <span class="rounded-full px-2 py-0.5 text-xs font-semibold {{ $s->paused ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800' }}">
                            {{ $s->paused ? 'En pausa' : 'Activo' }}
                        </span>
                    </div>
                    <div class="truncate text-sm text-slate-500">{{ $s->note ?: implode(', ', $s->emails) }}</div>
                    <div class="mt-2 flex flex-wrap gap-1.5 text-xs">
                        @php
                            $chips = array_filter([
                                count($s->emails) === 1 ? $s->emails[0] : count($s->emails).' correos',
                                count($s->regions ?? []) ? count($s->regions).' '.(count($s->regions) === 1 ? 'región' : 'regiones') : null,
                                count($s->keywords ?? []) ? count($s->keywords).' '.(count($s->keywords) === 1 ? 'palabra' : 'palabras') : null,
                                count($s->entities ?? []) ? count($s->entities).' '.(count($s->entities) === 1 ? 'entidad' : 'entidades') : null,
                                $s->include_uniq ? 'UNIQ' : null,
                                $s->hasJobs() ? 'Empleos'.($s->job_min_salary ? ' desde S/ '.number_format($s->job_min_salary) : '') : null,
                                $s->full_report ? null : 'Resumido',
                            ]);
                        @endphp
                        @foreach ($chips as $chip)
                            <span class="rounded-full border border-marca-200 bg-marca-50 px-2.5 py-0.5 text-marca-800">{{ $chip }}</span>
                        @endforeach
                    </div>
                </div>
                <div class="flex w-full items-center justify-between gap-2 sm:w-auto sm:flex-col sm:items-end">
                    <span class="text-xs text-slate-500">{{ $s->last_sent_at ? 'Último envío: '.$s->last_sent_at->translatedFormat('j M, H:i') : 'Aún sin envíos' }}</span>
                    <div class="flex items-center gap-1">
                        <form method="POST" action="{{ route('subscribers.toggle', $s) }}">@csrf @method('PATCH')
                            <button class="rounded-lg px-2.5 py-1.5 text-sm hover:bg-marca-50">{{ $s->paused ? 'Reanudar' : 'Pausar' }}</button>
                        </form>
                        <a href="{{ route('subscribers.create', ['from' => $s->id]) }}" class="rounded-lg px-2.5 py-1.5 text-sm hover:bg-marca-50">Duplicar</a>
                        <a href="{{ route('subscribers.edit', $s) }}" class="rounded-lg px-2.5 py-1.5 text-sm hover:bg-marca-50">Editar</a>
                        <form method="POST" action="{{ route('subscribers.destroy', $s) }}" onsubmit="return confirm('¿Eliminar a {{ addslashes($s->name) }}? Dejará de recibir informes.')">@csrf @method('DELETE')
                            <button class="rounded-lg px-2.5 py-1.5 text-sm text-red-700 hover:bg-red-50">Eliminar</button>
                        </form>
                    </div>
                </div>
            </div>
        </article>
    @empty
        <div class="rounded-2xl border border-dashed border-marca-200 bg-white px-6 py-14 text-center text-slate-500">
            @if ($q !== '') Nada coincide con «{{ $q }}».
            @else <b class="block text-slate-700">Aún no hay suscriptores</b> Crea el primero: sus correos, regiones y palabras clave.
            @endif
        </div>
    @endforelse
@endsection
