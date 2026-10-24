@extends('layouts.app')
@section('title', 'Cobros · '.$subscriber->name)

@php
    $status = $subscriber->billingStatus();
    $left = $subscriber->daysLeft();
    $input = 'w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm focus:border-marca-600 focus:outline-none focus:ring-4 focus:ring-marca-100';
    $money = config('panel.currency');
@endphp

@section('content')
    <a href="{{ route('subscribers.index') }}" class="text-sm text-marca-700 hover:underline">← Volver a la lista</a>
    <div class="mb-4 mt-2 flex flex-wrap items-center gap-3">
        <h1 class="text-xl font-semibold text-marca-950">Cobros de {{ $subscriber->name }}</h1>
        <span class="rounded-full px-2.5 py-0.5 text-xs font-semibold
            {{ ['ok' => 'bg-emerald-100 text-emerald-800', 'expiring' => 'bg-amber-100 text-amber-800', 'expired' => 'bg-red-100 text-red-800', 'none' => 'bg-slate-200 text-slate-700'][$status] }}">
            @if ($status === 'none') Sin pagos
            @elseif ($status === 'expired') Venció el {{ $subscriber->paid_until->format('d/m/Y') }}
            @else Vigente hasta el {{ $subscriber->paid_until->format('d/m/Y') }} ({{ $left === 0 ? 'último día' : "quedan $left días" }})
            @endif
        </span>
    </div>

    @if ($errors->any())
        <div role="alert" class="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            <ul class="list-disc pl-5">@foreach ($errors->all() as $e) <li>{{ $e }}</li> @endforeach</ul>
        </div>
    @endif

    <section class="mb-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 class="mb-1 font-semibold text-marca-950">Registrar un pago</h2>
        <p class="mb-4 text-sm text-slate-500">
            Normal: {{ $money }} {{ number_format(config('panel.price'), 2) }} por {{ config('panel.days') }} días.
            @if ($status === 'ok' || $status === 'expiring') Los días se suman al final del período actual. @else Los días cuentan desde hoy. @endif
        </p>
        <form method="POST" action="{{ route('subscribers.payments.store', $subscriber) }}" class="grid gap-4 sm:grid-cols-3">
            @csrf
            <div>
                <label for="amount" class="mb-1 block text-sm font-medium">Monto ({{ $money }})</label>
                <input id="amount" name="amount" type="number" step="0.01" min="0" value="{{ old('amount', config('panel.price')) }}" class="{{ $input }}">
            </div>
            <div>
                <label for="days" class="mb-1 block text-sm font-medium">Días</label>
                <input id="days" name="days" type="number" min="1" max="366" value="{{ old('days', config('panel.days')) }}" class="{{ $input }}">
            </div>
            <div>
                <label for="method" class="mb-1 block text-sm font-medium">Medio de pago</label>
                <select id="method" name="method" required class="{{ $input }}">
                    @foreach (config('panel.payment_methods') as $key => $label)
                        <option value="{{ $key }}" @selected(old('method', 'yape') === $key)>{{ $label }}</option>
                    @endforeach
                </select>
            </div>
            <div>
                <label for="reference" class="mb-1 block text-sm font-medium">N.º de operación (opcional)</label>
                <input id="reference" name="reference" maxlength="60" value="{{ old('reference') }}" class="{{ $input }}">
            </div>
            <div>
                <label for="paid_on" class="mb-1 block text-sm font-medium">Fecha del pago</label>
                <input id="paid_on" name="paid_on" type="date" max="{{ today()->toDateString() }}" value="{{ old('paid_on', today()->toDateString()) }}" class="{{ $input }}">
            </div>
            <div class="flex items-end">
                <button class="w-full rounded-xl bg-marca-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-marca-800">Registrar pago</button>
            </div>
        </form>
    </section>

    <section class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 class="mb-3 font-semibold text-marca-950">Historial</h2>
        @forelse ($payments as $p)
            <div class="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 py-2.5 text-sm first:border-t-0">
                <div>
                    <b>{{ $money }} {{ number_format((float) $p->amount, 2) }}</b>
                    <span class="text-slate-500">· {{ config('panel.payment_methods')[$p->method] ?? $p->method }}{{ $p->reference ? ' · op. '.$p->reference : '' }}</span>
                </div>
                <div class="text-slate-500">pagó el {{ $p->paid_on->format('d/m/Y') }} · cubre del {{ $p->period_start->format('d/m') }} al {{ $p->period_end->format('d/m/Y') }}</div>
            </div>
        @empty
            <p class="text-sm text-slate-500">Aún no hay pagos. Mientras no pague, no recibe informes.</p>
        @endforelse
    </section>
@endsection
