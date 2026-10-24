@extends('layouts.app')
@section('title', $subscriber->exists ? $subscriber->name : 'Nuevo suscriptor')

@php
    $editing = $subscriber->exists;
    $val = fn (string $field) => old($field, $subscriber->{$field} ?? []);
    $input = 'w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm focus:border-marca-600 focus:outline-none focus:ring-4 focus:ring-marca-100';
@endphp

@section('content')
    <a href="{{ route('subscribers.index') }}" class="text-sm text-marca-700 hover:underline">← Volver a la lista</a>
    <h1 class="mb-4 mt-2 text-xl font-semibold text-marca-950">{{ $editing ? 'Editar suscriptor' : 'Nuevo suscriptor' }}</h1>

    @if ($errors->any())
        <div role="alert" class="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            <b>Revisa lo siguiente:</b>
            <ul class="mt-1 list-disc pl-5">@foreach ($errors->all() as $e) <li>{{ $e }}</li> @endforeach</ul>
        </div>
    @endif

    <form method="POST" action="{{ $editing ? route('subscribers.update', $subscriber) : route('subscribers.store') }}" class="space-y-5">
        @csrf
        @if ($editing) @method('PUT') @endif

        <section class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 class="mb-4 font-semibold text-marca-950">Datos</h2>
            <div class="grid gap-4 sm:grid-cols-2">
                <div>
                    <label for="name" class="mb-1 block text-sm font-medium">Nombre</label>
                    <input id="name" name="name" value="{{ old('name', $subscriber->name) }}" maxlength="60" required class="{{ $input }}" placeholder="Ej.: Grupo Indescar">
                    <p class="mt-1 text-xs text-slate-500">Así lo ves en la lista; no sale en el correo.</p>
                </div>
                <div>
                    <label for="note" class="mb-1 block text-sm font-medium">Nota (opcional)</label>
                    <input id="note" name="note" value="{{ old('note', $subscriber->note) }}" maxlength="120" class="{{ $input }}" placeholder="Ej.: Cliente de cemento y fierro">
                </div>
            </div>
            <div class="mt-4">
                <label class="mb-1 block text-sm font-medium">Correos que reciben el informe</label>
                <div data-chips data-name="emails" data-values="{{ json_encode($val('emails')) }}" data-placeholder="Escribe un correo y pulsa Enter" data-email></div>
            </div>
            <div class="mt-4 grid gap-4 sm:grid-cols-2">
                <label class="flex items-start gap-3 rounded-xl border border-slate-200 p-3">
                    <input type="checkbox" name="full_report" value="1" @checked(old('full_report', $subscriber->full_report ?? true)) class="mt-1 rounded">
                    <span class="text-sm"><b>Informe completo cada día</b><br><span class="text-slate-500">Si lo quitas, lo ya informado sale resumido.</span></span>
                </label>
                <label class="flex items-start gap-3 rounded-xl border border-slate-200 p-3">
                    <input type="checkbox" name="include_uniq" value="1" @checked(old('include_uniq', $subscriber->include_uniq)) class="mt-1 rounded">
                    <span class="text-sm"><b>Cotizaciones de la UNIQ</b><br><span class="text-slate-500">Las cotizaciones en línea de la Universidad de Quillabamba.</span></span>
                </label>
            </div>
        </section>

        <section class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 class="mb-1 font-semibold text-marca-950">Compras públicas (SEACE)</h2>
            <p class="mb-4 text-sm text-slate-500">Las palabras clave se buscan <b>solo en las regiones</b> elegidas; sin regiones, en todo el país.</p>

            <label class="mb-1 block text-sm font-medium">Regiones</label>
            <div data-chips data-name="regions" data-values="{{ json_encode($val('regions')) }}" data-placeholder="Elige abajo una región" data-region-label data-readonly></div>
            <div data-region-picker data-target="regions" class="mt-2"></div>

            <label class="mb-1 mt-5 block text-sm font-medium">Palabras clave</label>
            <div data-chips data-name="keywords" data-values="{{ json_encode($val('keywords')) }}" data-placeholder="Escribe una palabra o frase y pulsa Enter" data-quote></div>
            <p class="mt-1 text-xs text-slate-500">Varias palabras sin comillas: deben estar todas en el proceso. Con el botón de comillas: juntas y en ese orden.</p>

            <label class="mb-1 mt-5 block text-sm font-medium">Entidades que sigue</label>
            <div data-chips data-name="entities" data-values="{{ json_encode($val('entities')) }}" data-placeholder="Parte del nombre: municipalidad, UGEL, red de salud…"></div>
            <p class="mt-1 text-xs text-slate-500">Recibe todo lo que tengan abierto, esté o no en sus regiones.</p>
        </section>

        <section class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 class="mb-1 font-semibold text-marca-950">Ofertas de empleo</h2>
            <p class="mb-4 text-sm text-slate-500">De Empleos Perú y Talento Perú (SERVIR). Se activan al llenar cualquiera de estos campos.</p>

            <label class="mb-1 block text-sm font-medium">Palabras del puesto</label>
            <div data-chips data-name="job_keywords" data-values="{{ json_encode($val('job_keywords')) }}" data-placeholder="Ej.: ingeniero, abogado, contador" data-quote></div>

            <label class="mb-1 mt-5 block text-sm font-medium">Regiones de empleo</label>
            <div data-chips data-name="job_regions" data-values="{{ json_encode($val('job_regions')) }}" data-placeholder="Vacío: usa las regiones de arriba" data-region-label data-readonly></div>
            <div data-region-picker data-target="job_regions" class="mt-2"></div>

            <div class="mt-5 max-w-xs">
                <label for="job_min_salary" class="mb-1 block text-sm font-medium">Sueldo mínimo mensual (S/)</label>
                <input id="job_min_salary" name="job_min_salary" type="number" min="0" step="100" inputmode="numeric"
                       value="{{ old('job_min_salary', $subscriber->job_min_salary) }}" class="{{ $input }}" placeholder="Ej.: 3000">
                <p class="mt-1 text-xs text-slate-500">Las ofertas sin sueldo publicado se siguen mostrando.</p>
            </div>
        </section>

        @if ($editing)
            <label class="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 text-sm">
                <input type="checkbox" name="paused" value="1" @checked(old('paused', $subscriber->paused)) class="rounded">
                <span><b>En pausa</b> — no se le envía nada hasta que lo quites.</span>
            </label>
        @endif

        <div class="flex justify-end gap-3">
            <a href="{{ route('subscribers.index') }}" class="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium hover:bg-marca-50">Cancelar</a>
            <button class="rounded-xl bg-marca-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-marca-800">Guardar</button>
        </div>
    </form>

    <script>
        const REGIONES = @json($regions);
        const esc = t => String(t).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

        // Etiquetas: cada una es un <input type="hidden" name="campo[]">; Enter o coma agrega, Retroceso quita la última.
        document.querySelectorAll('[data-chips]').forEach(box => {
            const name = box.dataset.name, values = JSON.parse(box.dataset.values || '[]'), quote = 'quote' in box.dataset;
            box.className = 'flex min-h-[46px] flex-wrap items-center gap-1.5 rounded-xl border border-slate-300 bg-white p-1.5 focus-within:border-marca-600 focus-within:ring-4 focus-within:ring-marca-100';
            const field = document.createElement('input');
            field.type = 'text'; field.placeholder = box.dataset.placeholder; field.autocomplete = 'off';
            field.className = 'min-w-[160px] flex-1 border-0 bg-transparent px-2 py-1.5 text-sm outline-none';
            if ('readonly' in box.dataset) field.readOnly = true;
            const shown = v => 'regionLabel' in box.dataset ? v.replace('/', ' › ') : v;
            const draw = () => {
                box.querySelectorAll('.chip').forEach(c => c.remove());
                values.forEach((v, i) => {
                    const exact = /^".*"$/.test(v), phrase = /\s/.test(v.replace(/"/g, ''));
                    const chip = document.createElement('span');
                    chip.className = 'chip inline-flex items-center gap-1 rounded-lg border border-marca-200 bg-marca-50 py-0.5 pl-2.5 pr-1 text-sm text-marca-800';
                    chip.innerHTML = `<input type="hidden" name="${name}[]" value="${esc(v)}">${esc(shown(v))}`
                        + (quote && phrase ? `<button type="button" data-q="${i}" title="Frase exacta: las palabras van juntas" class="rounded px-1 text-xs font-bold ${exact ? 'bg-marca-700 text-white' : 'text-marca-700 hover:bg-marca-100'}">“”</button>` : '')
                        + `<button type="button" data-x="${i}" aria-label="Quitar" class="rounded px-1.5 text-base leading-none hover:bg-marca-200">×</button>`;
                    box.insertBefore(chip, field);
                });
            };
            const add = raw => {
                const v = raw.replace(/,/g, ' ').replace(/\s+/g, ' ').trim();
                if (!v) return false;
                if ('email' in box.dataset && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)) { field.setCustomValidity('Ese correo no parece válido'); field.reportValidity(); field.setCustomValidity(''); return false; }
                if (!values.some(x => x.toLowerCase() === v.toLowerCase())) values.push(v);
                draw(); return true;
            };
            box.add = add;
            box.append(field); draw();
            field.addEventListener('keydown', e => {
                if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); if (add(field.value)) field.value = ''; }
                else if (e.key === 'Backspace' && !field.value && values.length) { values.pop(); draw(); }
            });
            field.addEventListener('blur', () => { if (add(field.value)) field.value = ''; });
            field.addEventListener('paste', e => {
                const t = e.clipboardData.getData('text');
                if (/[,;\n]/.test(t)) { e.preventDefault(); t.split(/[,;\n]+/).forEach(add); }
            });
            box.addEventListener('click', e => {
                const x = e.target.closest('[data-x]'), q = e.target.closest('[data-q]');
                if (x) { values.splice(+x.dataset.x, 1); draw(); }
                else if (q) { const i = +q.dataset.q, v = values[i]; values[i] = /^".*"$/.test(v) ? v.slice(1, -1) : `"${v}"`; draw(); }
                else field.focus();
            });
        });

        // Selector de región: departamento + provincia opcional -> agrega "CUSCO" o "CUSCO/LA CONVENCION".
        document.querySelectorAll('[data-region-picker]').forEach(host => {
            host.className = 'grid gap-2 sm:grid-cols-[1fr_1fr_auto]';
            const base = 'rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm focus:border-marca-600 focus:outline-none focus:ring-4 focus:ring-marca-100';
            host.innerHTML = `<select class="${base}" aria-label="Región"><option value="">Región…</option>${REGIONES.map(r => `<option>${esc(r.name)}</option>`).join('')}</select>
                <select class="${base}" aria-label="Provincia" disabled><option value="">Toda la región</option></select>
                <button type="button" class="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium hover:bg-marca-50">+ Agregar</button>`;
            const [dep, prov, btn] = host.children;
            dep.addEventListener('change', () => {
                const r = REGIONES.find(x => x.name === dep.value);
                prov.innerHTML = '<option value="">Toda la región</option>' + (r ? r.provinces.map(p => `<option>${esc(p)}</option>`).join('') : '');
                prov.disabled = !r;
            });
            btn.addEventListener('click', () => {
                if (!dep.value) return dep.focus();
                document.querySelector(`[data-chips][data-name="${host.dataset.target}"]`).add(dep.value + (prov.value ? '/' + prov.value : ''));
                dep.value = ''; dep.dispatchEvent(new Event('change'));
            });
        });
    </script>
@endsection
