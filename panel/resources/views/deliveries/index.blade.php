@extends('layouts.app')
@section('title', 'Envíos')
@section('wide', '1')

@php
    $prev = $date->copy()->subDay();
    $next = $date->copy()->addDay();
    $esHoy = $date->isToday();
    $correo = ['enviado' => ['green', 'Enviado'], 'error' => ['red', 'Error']];
    $telegram = ['enviado' => ['green', 'Enviado'], 'error' => ['red', 'Error'], 'sin_vincular' => ['slate', 'Sin vincular'], 'omitido' => ['slate', '—']];
    $max = max(1, $days->max(fn ($d) => $d['sent'] + $d['failed']));
@endphp

@section('content')
    {{-- Encabezado con el selector de fecha --}}
    <div class="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
            <h1 class="text-xl font-semibold text-marca-950">Envíos</h1>
            <p class="text-sm text-slate-500">Qué se envió y a quién le faltó, día por día.</p>
        </div>
        <form method="GET" class="flex items-center gap-2">
            <a href="{{ route('deliveries.index', ['fecha' => $prev->toDateString()]) }}" class="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-marca-50" aria-label="Día anterior">‹</a>
            <input type="date" name="fecha" value="{{ $date->toDateString() }}" max="{{ today()->toDateString() }}" onchange="this.form.submit()"
                   class="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm focus:border-marca-600 focus:outline-none focus:ring-4 focus:ring-marca-100">
            @if (! $esHoy)
                <a href="{{ route('deliveries.index', ['fecha' => $next->toDateString()]) }}" class="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-marca-50" aria-label="Día siguiente">›</a>
                <a href="{{ route('deliveries.index') }}" class="rounded-xl px-3 py-2 text-sm font-medium text-marca-700 hover:bg-marca-50">Hoy</a>
            @endif
        </form>
    </div>

    <div class="grid gap-5 xl:grid-cols-[240px_minmax(0,1fr)_320px]">
        {{-- Indicadores del día --}}
        <aside class="grid grid-cols-2 content-start gap-3 md:grid-cols-4 xl:grid-cols-1" aria-label="Resumen del día">
            <x-kpi label="Correos enviados" :value="$stats['sent']" tone="good" :hint="$date->translatedFormat('l j \d\e F')" />
            <x-kpi label="Con error" :value="$stats['failed']" tone="bad" hint="el bot lo intentó y falló" />
            <x-kpi label="Sin envío" :value="$stats['missing']" tone="warn" hint="debían recibir y no les llegó" />
            <x-kpi label="Telegram enviados" :value="$stats['telegram']" tone="muted" />
        </aside>

        <div class="min-w-0 space-y-5">
            {{-- Aviso cuando el informe diario no corrió --}}
            @if (! $dailyRan && $missing->isNotEmpty())
                <div class="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                    @if ($esHoy && now()->lt(today()->setTime(7, 15)))
                        El informe diario sale a las <b>07:00</b>: todavía no le toca.
                    @else
                        <b>El informe diario de las 07:00 no se registró este día.</b> Puede que el bot no haya corrido o que no haya
                        podido avisar al panel. Revisa en el VPS: <code class="rounded bg-white/70 px-1">tail -n 30 /opt/cotizaciones-uniq/logs/bot.log</code>
                    @endif
                </div>
            @endif

            {{-- Envíos registrados --}}
            <x-card class="!p-0" >
                <div class="border-b border-slate-100 px-4 py-3">
                    <h2 class="text-sm font-semibold text-marca-950">Envíos registrados</h2>
                    <p class="text-xs text-slate-500">Cada vez que el bot procesó a un suscriptor (diario a las 07:00, tras un pago o manual).</p>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full min-w-[640px] text-left text-sm">
                        <thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                            <tr>
                                <th class="px-4 py-2.5 font-medium">Hora</th>
                                <th class="px-3 py-2.5 font-medium">Suscriptor</th>
                                <th class="px-3 py-2.5 font-medium">Tipo</th>
                                <th class="px-3 py-2.5 font-medium">Correo</th>
                                <th class="px-3 py-2.5 font-medium">Telegram</th>
                                <th class="px-4 py-2.5 font-medium">Detalle</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-100">
                            @forelse ($deliveries as $d)
                                <tr>
                                    <td class="whitespace-nowrap px-4 py-2.5 text-slate-600">{{ $d->created_at->format('H:i') }}</td>
                                    <td class="px-3 py-2.5 font-medium">
                                        @if ($d->subscriber)
                                            <a href="{{ route('subscribers.edit', $d->subscriber) }}" class="hover:text-marca-700">{{ $d->subscriber->name }}</a>
                                        @else
                                            {{ $d->subscriber_name }} <span class="text-xs font-normal text-slate-400">(eliminado)</span>
                                        @endif
                                    </td>
                                    <td class="px-3 py-2.5 text-slate-600">{{ \App\Models\Delivery::KINDS[$d->kind] ?? $d->kind }}</td>
                                    <td class="px-3 py-2.5"><x-badge :tone="$correo[$d->email_status][0] ?? 'slate'">{{ $correo[$d->email_status][1] ?? $d->email_status }}</x-badge></td>
                                    <td class="px-3 py-2.5"><x-badge :tone="$telegram[$d->telegram_status][0] ?? 'slate'">{{ $telegram[$d->telegram_status][1] ?? $d->telegram_status }}</x-badge></td>
                                    <td class="max-w-xs truncate px-4 py-2.5 text-xs text-slate-500" title="{{ $d->detail }}">{{ $d->detail }}</td>
                                </tr>
                            @empty
                                <tr><td colspan="6" class="px-4 py-10 text-center text-slate-500">No hay envíos registrados este día.</td></tr>
                            @endforelse
                        </tbody>
                    </table>
                </div>
            </x-card>

            {{-- A quién le faltó --}}
            <x-card title="Sin envío este día" subtitle="Tenían el servicio vigente y no les llegó el correo.">
                @forelse ($missing as $s)
                    <div class="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 py-2.5 text-sm first:border-t-0">
                        <div>
                            <a href="{{ route('subscribers.edit', $s) }}" class="font-medium hover:text-marca-700">{{ $s->name }}</a>
                            <span class="text-xs text-slate-500">· {{ implode(', ', $s->emails) }}</span>
                        </div>
                        @if ($esHoy)
                            <form method="POST" action="{{ route('subscribers.send-now', $s) }}">@csrf
                                <button class="rounded-lg px-2.5 py-1 text-sm font-medium text-marca-700 hover:bg-marca-50">Enviar ahora</button>
                            </form>
                        @endif
                    </div>
                @empty
                    <p class="text-sm text-slate-500">A nadie le faltó el informe este día.</p>
                @endforelse
            </x-card>
        </div>

        {{-- Últimos 14 días --}}
        <aside aria-label="Últimos 14 días">
            <x-card title="Últimos 14 días" subtitle="Correos enviados y con error por día">
                <ul class="space-y-1.5">
                    @foreach ($days->reverse() as $day)
                        <li>
                            <a href="{{ route('deliveries.index', ['fecha' => $day['date']->toDateString()]) }}"
                               @class(['grid grid-cols-[64px_1fr_auto] items-center gap-2 rounded-lg px-1.5 py-1 text-xs hover:bg-marca-50', 'bg-marca-50' => $day['date']->isSameDay($date)])>
                                <span class="text-slate-600">{{ $day['date']->translatedFormat('D j M') }}</span>
                                <span class="flex h-2 overflow-hidden rounded-full bg-slate-100">
                                    <span class="bg-emerald-500" style="width: {{ round($day['sent'] / $max * 100) }}%"></span>
                                    <span class="bg-red-500" style="width: {{ round($day['failed'] / $max * 100) }}%"></span>
                                </span>
                                <span class="w-14 text-right {{ $day['ran'] ? 'text-slate-700' : 'text-amber-600' }}">
                                    {{ $day['sent'] }}@if ($day['failed'])<span class="text-red-600"> · {{ $day['failed'] }}</span>@endif
                                    @unless ($day['ran'])<span title="El informe diario no se registró">!</span>@endunless
                                </span>
                            </a>
                        </li>
                    @endforeach
                </ul>
                <p class="mt-3 text-xs text-slate-500"><span class="text-emerald-600">■</span> enviados · <span class="text-red-600">■</span> con error · <span class="text-amber-600">!</span> no corrió el diario</p>
            </x-card>
        </aside>
    </div>
@endsection
