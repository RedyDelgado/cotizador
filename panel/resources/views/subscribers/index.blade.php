@extends('layouts.app')
@section('wide', '1')

@php
    $k = $stats['kpis'];
    $money = config('panel.currency');
    $filters = ['' => 'Todos', 'vigentes' => 'Vigentes', 'por-vencer' => 'Por vencer', 'vencidos' => 'Vencidos', 'sin-pago' => 'Sin pago', 'pausados' => 'En pausa'];
@endphp

@section('content')
    <div class="grid gap-5 xl:grid-cols-[240px_minmax(0,1fr)_320px]">

        {{-- Izquierda: indicadores --}}
        <aside class="grid grid-cols-2 content-start gap-3 md:grid-cols-3 xl:grid-cols-1" aria-label="Indicadores">
            <x-kpi label="Suscriptores" :value="$k['total']" :hint="$k['paused'].' en pausa'" />
            <x-kpi label="Con servicio vigente" :value="$k['paying']" tone="good" :hint="$k['total'] ? round($k['paying'] / $k['total'] * 100).'% del total' : null" :href="route('subscribers.index', ['estado' => 'vigentes'])" />
            <x-kpi label="Por vencer" :value="$k['expiring']" tone="warn" :hint="'en '.config('panel.expiring_days').' días o menos'" :href="route('subscribers.index', ['estado' => 'por-vencer'])" />
            <x-kpi label="Vencidos o sin pago" :value="$k['overdue']" tone="bad" hint="no reciben informes" :href="route('subscribers.index', ['estado' => 'vencidos'])" />
            <x-kpi label="Cobrado este mes" :value="$money.' '.number_format($k['income'], 2)" :trend="$k['income_trend']" hint="frente al mes anterior" />
            <x-kpi label="Con Telegram" :value="$k['telegram']" tone="muted" :hint="$k['telegram_pct'].'% vinculado'" />
        </aside>

        {{-- Centro: registros --}}
        <x-card class="min-w-0 !p-0">
            <div class="flex flex-col gap-3 border-b border-slate-100 p-4 lg:flex-row lg:items-center">
                <form method="GET" class="flex flex-1 flex-wrap gap-2" role="search">
                    <input type="search" name="q" value="{{ $q }}" placeholder="Buscar nombre, correo, región, palabra o entidad"
                           class="min-w-[200px] flex-1 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm focus:border-marca-600 focus:outline-none focus:ring-4 focus:ring-marca-100">
                    <select name="estado" onchange="this.form.submit()" aria-label="Estado"
                            class="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm focus:border-marca-600 focus:outline-none focus:ring-4 focus:ring-marca-100">
                        @foreach ($filters as $value => $label)
                            <option value="{{ $value }}" @selected($status === (string) $value)>{{ $label }}</option>
                        @endforeach
                    </select>
                    <button class="rounded-xl border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-marca-50">Buscar</button>
                </form>
                <a href="{{ route('subscribers.create') }}" class="rounded-xl bg-marca-700 px-4 py-2 text-center text-sm font-semibold text-white hover:bg-marca-800">+ Nuevo suscriptor</a>
            </div>

            <div class="overflow-x-auto">
                <table class="w-full min-w-[760px] text-left text-sm">
                    <thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                        <tr>
                            <th class="px-4 py-2.5 font-medium">Suscriptor</th>
                            <th class="px-3 py-2.5 font-medium">Servicio</th>
                            <th class="px-3 py-2.5 font-medium">Sigue</th>
                            <th class="px-3 py-2.5 font-medium">Último envío</th>
                            <th class="px-4 py-2.5 text-right font-medium">Acciones</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100">
                        @forelse ($subscribers as $s)
                            @php
                                $billing = $s->billingStatus();
                                $left = $s->daysLeft();
                            @endphp
                            <tr class="{{ $s->paused ? 'opacity-60' : '' }} hover:bg-marca-50/40">
                                <td class="px-4 py-3">
                                    <div class="flex items-center gap-3">
                                        <div class="flex h-9 w-9 flex-none items-center justify-center rounded-lg bg-marca-700 text-xs font-semibold text-white">{{ mb_strtoupper(mb_substr($s->name, 0, 2)) }}</div>
                                        <div class="min-w-0">
                                            <a href="{{ route('subscribers.edit', $s) }}" class="block truncate font-medium text-slate-900 hover:text-marca-700">{{ $s->name }}</a>
                                            <div class="truncate text-xs text-slate-500">{{ count($s->emails) === 1 ? $s->emails[0] : count($s->emails).' correos' }}{{ $s->telegram_chat_id ? ' · Telegram' : '' }}</div>
                                        </div>
                                    </div>
                                </td>
                                <td class="px-3 py-3">
                                    @if ($s->paused) <x-badge tone="amber">En pausa</x-badge>
                                    @elseif ($billing === 'none') <x-badge>Sin pagos</x-badge>
                                    @elseif ($billing === 'expired') <x-badge tone="red">Venció {{ $s->paid_until->format('d/m') }}</x-badge>
                                    @else <x-badge :tone="$billing === 'ok' ? 'green' : 'amber'">{{ $left === 0 ? 'Último día' : "Quedan $left d" }}</x-badge>
                                    @endif
                                    @if ($s->paid_until)<div class="mt-0.5 text-xs text-slate-500">hasta {{ $s->paid_until->format('d/m/Y') }}</div>@endif
                                </td>
                                <td class="px-3 py-3">
                                    <div class="flex flex-wrap gap-1">
                                        @foreach (array_filter([
                                            count($s->regions ?? []) ? count($s->regions).' reg.' : null,
                                            count($s->keywords ?? []) ? count($s->keywords).' palabras' : null,
                                            count($s->entities ?? []) ? count($s->entities).' entid.' : null,
                                            $s->include_uniq ? 'UNIQ' : null,
                                            $s->hasJobs() ? 'Empleos'.($s->job_min_salary ? ' ≥ '.number_format($s->job_min_salary) : '') : null,
                                        ]) as $chip)
                                            <x-badge tone="violet">{{ $chip }}</x-badge>
                                        @endforeach
                                    </div>
                                </td>
                                <td class="whitespace-nowrap px-3 py-3 text-xs text-slate-500">{{ $s->last_sent_at ? $s->last_sent_at->translatedFormat('j M, H:i') : 'Aún sin envíos' }}</td>
                                <td class="px-4 py-3">
                                    <div class="flex items-center justify-end gap-1">
                                        <a href="{{ route('subscribers.payments.index', $s) }}" class="rounded-lg px-2 py-1 text-sm font-medium text-marca-700 hover:bg-marca-50">Cobros</a>
                                        <a href="{{ route('subscribers.edit', $s) }}" class="rounded-lg px-2 py-1 text-sm text-slate-600 hover:bg-marca-50">Editar</a>
                                        <x-dropdown>
                                            <a href="{{ route('subscribers.create', ['from' => $s->id]) }}" class="block rounded-lg px-3 py-1.5 text-sm hover:bg-marca-50">Duplicar</a>
                                            <form method="POST" action="{{ route('subscribers.send-now', $s) }}">@csrf
                                                <button class="block w-full rounded-lg px-3 py-1.5 text-left text-sm hover:bg-marca-50">Enviar informe ahora</button>
                                            </form>
                                            <form method="POST" action="{{ route('subscribers.toggle', $s) }}">@csrf @method('PATCH')
                                                <button class="block w-full rounded-lg px-3 py-1.5 text-left text-sm hover:bg-marca-50">{{ $s->paused ? 'Reanudar' : 'Pausar' }}</button>
                                            </form>
                                            <form method="POST" action="{{ route('subscribers.destroy', $s) }}" onsubmit="return confirm('¿Eliminar a {{ addslashes($s->name) }}? Dejará de recibir informes.')">@csrf @method('DELETE')
                                                <button class="block w-full rounded-lg px-3 py-1.5 text-left text-sm text-red-700 hover:bg-red-50">Eliminar</button>
                                            </form>
                                        </x-dropdown>
                                    </div>
                                </td>
                            </tr>
                        @empty
                            <tr>
                                <td colspan="5" class="px-4 py-14 text-center text-slate-500">
                                    @if ($q !== '' || $status !== '') Nada coincide con el filtro.
                                    @else <b class="block text-slate-700">Aún no hay suscriptores</b> Crea el primero: sus correos, regiones y palabras clave.
                                    @endif
                                </td>
                            </tr>
                        @endforelse
                    </tbody>
                </table>
            </div>

            <x-pagination :paginator="$subscribers" class="border-t border-slate-100 p-4" />
        </x-card>

        {{-- Derecha: gráficos --}}
        <aside class="grid content-start gap-4 md:grid-cols-2 xl:grid-cols-1" aria-label="Gráficos">
            <x-card title="Estado de las suscripciones" subtitle="Cuántos reciben informes hoy">
                <x-donut-chart :segments="$stats['status']" :center="$k['total']" caption="Suscriptores por estado" />
            </x-card>

            <x-card title="Ingresos por mes" subtitle="Últimos 6 meses">
                <x-column-chart :items="$stats['income']" :prefix="$money.' '" />
            </x-card>

            <x-card title="Próximos vencimientos" subtitle="A quién cobrar primero">
                @forelse ($stats['expiring'] as $s)
                    <a href="{{ route('subscribers.payments.index', $s) }}" class="flex items-center justify-between gap-2 border-t border-slate-100 py-2 text-sm first:border-t-0 hover:text-marca-700">
                        <span class="truncate">{{ $s->name }}</span>
                        <x-badge tone="amber">{{ $s->daysLeft() === 0 ? 'hoy' : $s->daysLeft().' d' }}</x-badge>
                    </a>
                @empty
                    <p class="text-xs text-slate-500">Nadie vence en los próximos {{ config('panel.expiring_days') }} días.</p>
                @endforelse
            </x-card>

            <x-card title="Regiones más seguidas">
                <x-bar-list :items="$stats['regions']" empty="Aún no hay regiones registradas." />
            </x-card>

            <x-card title="Palabras clave más usadas">
                <x-bar-list :items="$stats['keywords']" color="#8B5CF6" empty="Aún no hay palabras clave." />
            </x-card>
        </aside>
    </div>
@endsection
