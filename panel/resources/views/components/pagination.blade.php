{{-- Paginación con «Mostrando X–Y de N». paginator: LengthAwarePaginator (con withQueryString()). --}}
@props(['paginator'])

@php
    $current = $paginator->currentPage();
    $last = $paginator->lastPage();
    $pages = collect(range(max(1, $current - 2), min($last, $current + 2)));
    $link = 'inline-flex h-8 min-w-8 items-center justify-center rounded-lg border px-2 text-sm';
@endphp

<nav {{ $attributes->class(['flex flex-wrap items-center justify-between gap-3 text-sm']) }} aria-label="Paginación">
    <p class="text-slate-500">
        @if ($paginator->total() > 0) Mostrando <b>{{ $paginator->firstItem() }}–{{ $paginator->lastItem() }}</b> de <b>{{ $paginator->total() }}</b>
        @else Sin resultados @endif
    </p>

    @if ($last > 1)
        <div class="flex items-center gap-1">
            @if ($paginator->onFirstPage())
                <span class="{{ $link }} border-slate-200 text-slate-300">‹</span>
            @else
                <a href="{{ $paginator->previousPageUrl() }}" rel="prev" class="{{ $link }} border-slate-300 hover:bg-marca-50" aria-label="Anterior">‹</a>
            @endif

            @if ($pages->first() > 1)
                <a href="{{ $paginator->url(1) }}" class="{{ $link }} border-slate-300 hover:bg-marca-50">1</a>
                @if ($pages->first() > 2) <span class="px-1 text-slate-400">…</span> @endif
            @endif
            @foreach ($pages as $page)
                @if ($page === $current)
                    <span aria-current="page" class="{{ $link }} border-marca-700 bg-marca-700 font-semibold text-white">{{ $page }}</span>
                @else
                    <a href="{{ $paginator->url($page) }}" class="{{ $link }} border-slate-300 hover:bg-marca-50">{{ $page }}</a>
                @endif
            @endforeach
            @if ($pages->last() < $last)
                @if ($pages->last() < $last - 1) <span class="px-1 text-slate-400">…</span> @endif
                <a href="{{ $paginator->url($last) }}" class="{{ $link }} border-slate-300 hover:bg-marca-50">{{ $last }}</a>
            @endif

            @if ($paginator->hasMorePages())
                <a href="{{ $paginator->nextPageUrl() }}" rel="next" class="{{ $link }} border-slate-300 hover:bg-marca-50" aria-label="Siguiente">›</a>
            @else
                <span class="{{ $link }} border-slate-200 text-slate-300">›</span>
            @endif
        </div>
    @endif
</nav>
