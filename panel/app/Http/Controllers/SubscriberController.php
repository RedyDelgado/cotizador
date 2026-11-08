<?php

namespace App\Http\Controllers;

use App\Http\Requests\StoreSubscriberRequest;
use App\Http\Requests\UpdateSubscriberRequest;
use App\Models\Subscriber;
use App\Services\Telegram;
use App\Support\Regions;
use App\Support\SubscriberStats;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\View\View;

/** Panel de administración (sesión). Usa las mismas validaciones que la API. */
class SubscriberController extends Controller
{
    public function index(Request $request): View
    {
        $status = $request->query('estado');
        $subscribers = Subscriber::query()
            ->search($request->query('q'))
            ->billing($status)
            ->latest()      // los más nuevos primero (fecha de creación; el id desempata)
            ->latest('id')
            ->paginate(10)
            ->withQueryString();

        return view('subscribers.index', [
            'subscribers' => $subscribers,
            'stats' => SubscriberStats::make(),
            'q' => (string) $request->query('q'),
            'status' => (string) $status,
        ]);
    }

    public function create(Request $request): View
    {
        // "Duplicar": /subscribers/create?from=ID precarga los intereses de otro suscriptor.
        $template = $request->integer('from') ? Subscriber::find($request->integer('from')) : null;
        $subscriber = $template ? $template->replicate(['last_sent_at', 'paused', 'state_key', 'paid_until', 'telegram_chat_id', 'telegram_link_code', 'last_reminder'])->fill(['name' => $template->name.' (copia)']) : new Subscriber(['full_report' => true]);

        return view('subscribers.form', ['subscriber' => $subscriber, 'regions' => Regions::forForm(), 'telegramLink' => null]);
    }

    public function store(StoreSubscriberRequest $request): RedirectResponse
    {
        $subscriber = Subscriber::create($request->validated());

        return redirect()->route('subscribers.payments.index', $subscriber)->with('status', "{$subscriber->name} agregado. Registra su primer pago para que empiece a recibir informes.");
    }

    public function edit(Subscriber $subscriber, Telegram $telegram): View
    {
        return view('subscribers.form', ['subscriber' => $subscriber, 'regions' => Regions::forForm(), 'telegramLink' => $telegram->linkFor($subscriber->telegram_link_code)]);
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

    /** «Enviar ahora»: el bot lo recoge en unos minutos. Solo si tiene el servicio vigente. */
    public function sendNow(Subscriber $subscriber): RedirectResponse
    {
        if ($subscriber->paused || ! $subscriber->paid_until || $subscriber->paid_until->lt(today())) {
            return back()->with('status', "{$subscriber->name} no tiene el servicio vigente: no se le envía nada.");
        }
        $subscriber->update(['send_now' => true]);

        return back()->with('status', "{$subscriber->name}: el informe sale en unos minutos.");
    }

    public function toggle(Subscriber $subscriber): RedirectResponse
    {
        $subscriber->update(['paused' => ! $subscriber->paused]);

        return back()->with('status', $subscriber->paused ? "{$subscriber->name}: envíos en pausa." : "{$subscriber->name}: envíos reanudados.");
    }
}
