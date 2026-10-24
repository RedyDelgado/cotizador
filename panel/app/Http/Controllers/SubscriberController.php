<?php

namespace App\Http\Controllers;

use App\Http\Requests\StoreSubscriberRequest;
use App\Http\Requests\UpdateSubscriberRequest;
use App\Models\Subscriber;
use App\Support\Regions;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\View\View;

/** Panel de administración (sesión). Usa las mismas validaciones que la API. */
class SubscriberController extends Controller
{
    public function index(Request $request): View
    {
        $subscribers = Subscriber::query()->search($request->query('q'))->orderBy('name')->get();

        return view('subscribers.index', [
            'subscribers' => $subscribers,
            'total' => Subscriber::count(),
            'active' => Subscriber::active()->count(),
            'q' => (string) $request->query('q'),
        ]);
    }

    public function create(Request $request): View
    {
        // "Duplicar": /subscribers/create?from=ID precarga los intereses de otro suscriptor.
        $template = $request->integer('from') ? Subscriber::find($request->integer('from')) : null;
        $subscriber = $template ? $template->replicate(['last_sent_at', 'paused'])->fill(['name' => $template->name.' (copia)']) : new Subscriber(['full_report' => true]);

        return view('subscribers.form', ['subscriber' => $subscriber, 'regions' => Regions::forForm()]);
    }

    public function store(StoreSubscriberRequest $request): RedirectResponse
    {
        $subscriber = Subscriber::create($request->validated());

        return redirect()->route('subscribers.index')->with('status', "{$subscriber->name} agregado.");
    }

    public function edit(Subscriber $subscriber): View
    {
        return view('subscribers.form', ['subscriber' => $subscriber, 'regions' => Regions::forForm()]);
    }

    public function update(UpdateSubscriberRequest $request, Subscriber $subscriber): RedirectResponse
    {
        $subscriber->update($request->validated());

        return redirect()->route('subscribers.index')->with('status', "{$subscriber->name} guardado.");
    }

    public function destroy(Subscriber $subscriber): RedirectResponse
    {
        $subscriber->delete();

        return redirect()->route('subscribers.index')->with('status', "{$subscriber->name} eliminado.");
    }

    public function toggle(Subscriber $subscriber): RedirectResponse
    {
        $subscriber->update(['paused' => ! $subscriber->paused]);

        return back()->with('status', $subscriber->paused ? "{$subscriber->name}: envíos en pausa." : "{$subscriber->name}: envíos reanudados.");
    }
}
