<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>@yield('title', 'Suscriptores') · NEOESTADO</title>
    @vite('resources/css/app.css')
</head>
<body class="min-h-screen bg-slate-100 text-slate-900">
<header class="sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur">
    <div class="mx-auto flex max-w-5xl items-center gap-3 px-4 py-3">
        <img src="{{ asset('logo.png') }}" alt="" class="h-10 w-10 rounded-lg" onerror="this.remove()">
        <div class="leading-tight">
            <div class="font-semibold text-marca-950">Suscriptores</div>
            <div class="text-xs text-slate-500">NEOESTADO · quién recibe qué</div>
        </div>
        <div class="flex-1"></div>
        @auth
            <span class="hidden text-sm text-slate-500 sm:inline">{{ auth()->user()->email }}</span>
            <form method="POST" action="{{ route('logout') }}">@csrf
                <button class="rounded-xl border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-marca-50">Salir</button>
            </form>
        @endauth
    </div>
</header>

<main class="mx-auto max-w-5xl px-4 pb-24 pt-6">
    @if (session('status'))
        <div role="status" class="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{{ session('status') }}</div>
    @endif
    @yield('content')
</main>
</body>
</html>
