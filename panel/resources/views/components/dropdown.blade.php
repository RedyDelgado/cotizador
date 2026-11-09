{{-- Menú desplegable (details). El menú flota sobre la página (position: fixed): así no lo recorta una tabla con
     desplazamiento lateral. label: texto del botón; el contenido va en el slot. --}}
@props(['label' => 'Más'])

<details {{ $attributes->class(['relative']) }} data-dropdown>
    <summary class="flex cursor-pointer list-none items-center rounded-lg px-2 py-1 text-sm text-slate-600 marker:hidden hover:bg-marca-50 [&::-webkit-details-marker]:hidden">{{ $label }} ▾</summary>
    <div data-dropdown-menu class="fixed z-50 w-48 rounded-xl border border-slate-200 bg-white p-1 shadow-lg">
        {{ $slot }}
    </div>
</details>

@once
    <script>
        (() => {
            const cerrarTodos = (excepto) => document.querySelectorAll('details[data-dropdown][open]').forEach(d => d !== excepto && d.removeAttribute('open'));
            const ubicar = (d) => {
                const boton = d.querySelector('summary').getBoundingClientRect();
                const menu = d.querySelector('[data-dropdown-menu]');
                const alto = menu.offsetHeight, ancho = menu.offsetWidth;
                const abajo = boton.bottom + 4 + alto <= window.innerHeight;           // si no cabe abajo, se abre hacia arriba
                menu.style.top = (abajo ? boton.bottom + 4 : Math.max(8, boton.top - alto - 4)) + 'px';
                menu.style.left = Math.max(8, Math.min(boton.right - ancho, window.innerWidth - ancho - 8)) + 'px';
            };
            document.addEventListener('toggle', (e) => {
                const d = e.target;
                if (!(d instanceof HTMLDetailsElement) || !d.matches('[data-dropdown]') || !d.open) return;
                cerrarTodos(d);
                ubicar(d);
            }, true);
            document.addEventListener('click', (e) => { if (!e.target.closest('details[data-dropdown]')) cerrarTodos(null); });
            document.addEventListener('keydown', (e) => { if (e.key === 'Escape') cerrarTodos(null); });
            // al desplazar o cambiar el tamaño, el menú se cerraría lejos de su botón: mejor cerrarlo
            window.addEventListener('resize', () => cerrarTodos(null));
            document.addEventListener('scroll', () => cerrarTodos(null), true);
        })();
    </script>
@endonce
