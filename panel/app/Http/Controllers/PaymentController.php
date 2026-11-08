<?php

namespace App\Http\Controllers;

use App\Http\Requests\StorePaymentRequest;
use App\Models\Subscriber;
use App\Services\Telegram;
use Illuminate\Http\RedirectResponse;
use Illuminate\View\View;

/** Cobros de un suscriptor en el panel web. */
class PaymentController extends Controller
{
    public function index(Subscriber $subscriber): View
    {
        return view('subscribers.payments', ['subscriber' => $subscriber, 'payments' => $subscriber->payments()->get()]);
    }

    public function store(StorePaymentRequest $request, Subscriber $subscriber, Telegram $telegram): RedirectResponse
    {
        $payment = $subscriber->registerPayment($request->paymentData());

        if ($subscriber->telegram_chat_id) { // confirmación al suscriptor, si ya vinculó su Telegram
            $telegram->send($subscriber->telegram_chat_id, 'Recibimos tu pago de '.config('panel.currency').' '.number_format((float) $payment->amount, 2)
                .'. Tu servicio está vigente hasta el <b>'.$payment->period_end->format('d/m/Y').'</b>. Gracias.');
        }

        return redirect()->route('subscribers.payments.index', $subscriber)
            ->with('status', 'Pago registrado: vigente hasta el '.$payment->period_end->format('d/m/Y').'.'.($subscriber->send_now ? ' Su primer informe sale en unos minutos.' : ''));
    }
}
