<?php

namespace App\Http\Controllers;

use App\Models\Delivery;
use App\Models\Subscriber;
use Illuminate\Http\Request;
use Illuminate\Support\Carbon;
use Illuminate\View\View;

/** Módulo «Envíos»: qué se envió y a quién le faltó, día por día. */
class DeliveryController extends Controller
{
    public function index(Request $request): View
    {
        $date = $this->date($request->query('fecha'));
        $deliveries = Delivery::whereDate('run_date', $date)->latest()->latest('id')->get();

        // Quiénes debían recibir el informe diario ese día: no pausados (estado actual) y con el pago vigente ese día.
        $expected = Subscriber::where('paused', false)
            ->whereDate('paid_until', '>=', $date)
            ->where('created_at', '<=', $date->copy()->endOfDay())
            ->orderBy('name')->get();
        $received = $deliveries->where('email_status', 'enviado')->pluck('subscriber_id')->filter()->all();
        $missing = $expected->reject(fn (Subscriber $s) => in_array($s->id, $received, true))->values();

        $from = $date->copy()->subDays(13);
        $history = Delivery::whereBetween('run_date', [$from->toDateString(), $date->toDateString()])->get()
            ->groupBy(fn (Delivery $d) => $d->run_date->toDateString());
        $days = collect(range(0, 13))->map(function (int $i) use ($from, $history) {
            $day = $from->copy()->addDays($i);
            $rows = $history->get($day->toDateString(), collect());

            return [
                'date' => $day,
                'sent' => $rows->where('email_status', 'enviado')->count(),
                'failed' => $rows->where('email_status', 'error')->count(),
                'ran' => $rows->where('kind', 'diario')->isNotEmpty(),
            ];
        });

        return view('deliveries.index', [
            'date' => $date,
            'deliveries' => $deliveries,
            'missing' => $missing,
            'dailyRan' => $deliveries->where('kind', 'diario')->isNotEmpty(),
            'days' => $days,
            'stats' => [
                'sent' => $deliveries->where('email_status', 'enviado')->count(),
                'failed' => $deliveries->where('email_status', 'error')->count(),
                'missing' => $missing->count(),
                'telegram' => $deliveries->where('telegram_status', 'enviado')->count(),
            ],
        ]);
    }

    private function date(?string $value): Carbon
    {
        try {
            $date = $value ? Carbon::createFromFormat('Y-m-d', $value)->startOfDay() : today();
        } catch (\Throwable) {
            $date = today();
        }

        return $date->gt(today()) ? today() : $date;
    }
}
