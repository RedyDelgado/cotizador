<?php

namespace App\Support;

use App\Models\Payment;
use App\Models\Subscriber;
use Illuminate\Support\Collection;
use Illuminate\Support\Str;

/** Números del tablero (KPIs y gráficos) calculados a partir de los suscriptores y sus pagos. */
class SubscriberStats
{
    /**
     * @return array{
     *   kpis: array<string, mixed>,
     *   status: array<int, array{label: string, value: int, color: string}>,
     *   income: array<int, array{label: string, value: float}>,
     *   regions: array<int, array{label: string, value: int}>,
     *   keywords: array<int, array{label: string, value: int}>,
     *   expiring: Collection<int, Subscriber>
     * }
     */
    public static function make(): array
    {
        $all = Subscriber::all();
        $today = today();
        $expiringDays = (int) config('panel.expiring_days');

        $byStatus = $all->groupBy(fn (Subscriber $s) => $s->paused ? 'paused' : $s->billingStatus());
        $count = fn (string $key) => $byStatus->get($key, collect())->count();
        $paying = $count('ok') + $count('expiring');

        $thisMonth = (float) Payment::whereBetween('paid_on', [$today->copy()->startOfMonth(), $today->copy()->endOfMonth()])->sum('amount');
        $lastMonth = (float) Payment::whereBetween('paid_on', [$today->copy()->subMonthNoOverflow()->startOfMonth(), $today->copy()->subMonthNoOverflow()->endOfMonth()])->sum('amount');

        return [
            'kpis' => [
                'total' => $all->count(),
                'paying' => $paying,
                'expiring' => $count('expiring'),
                'overdue' => $count('expired') + $count('none'),
                'paused' => $count('paused'),
                'income' => $thisMonth,
                'income_trend' => $lastMonth > 0 ? round(($thisMonth - $lastMonth) / $lastMonth * 100) : null,
                'telegram' => $all->filter(fn (Subscriber $s) => (bool) $s->telegram_chat_id)->count(),
                'telegram_pct' => $all->count() ? (int) round($all->filter(fn (Subscriber $s) => (bool) $s->telegram_chat_id)->count() / $all->count() * 100) : 0,
            ],
            'status' => [
                ['label' => 'Vigentes', 'value' => $count('ok'), 'color' => '#10B981'],
                ['label' => 'Por vencer', 'value' => $count('expiring'), 'color' => '#F59E0B'],
                ['label' => 'Vencidos o sin pago', 'value' => $count('expired') + $count('none'), 'color' => '#EF4444'],
                ['label' => 'En pausa', 'value' => $count('paused'), 'color' => '#94A3B8'],
            ],
            'income' => self::incomeByMonth(6),
            'regions' => self::top($all, ['regions', 'job_regions'], 5, fn (string $r) => Str::title(Str::lower(str_replace('/', ' › ', $r)))),
            'keywords' => self::top($all, ['keywords', 'job_keywords'], 6, fn (string $k) => trim($k, '"')),
            'expiring' => $all->filter(fn (Subscriber $s) => ! $s->paused && $s->daysLeft() !== null && $s->daysLeft() <= $expiringDays && $s->daysLeft() >= 0)
                ->sortBy(fn (Subscriber $s) => $s->daysLeft())->take(5)->values(),
        ];
    }

    /** @return array<int, array{label: string, value: float}> */
    private static function incomeByMonth(int $months): array
    {
        $start = today()->startOfMonth()->subMonthsNoOverflow($months - 1);
        $sums = Payment::where('paid_on', '>=', $start)->get(['paid_on', 'amount'])
            ->groupBy(fn (Payment $p) => $p->paid_on->format('Y-m'))
            ->map(fn (Collection $group) => (float) $group->sum('amount'));

        $series = [];
        for ($i = 0; $i < $months; $i++) {
            $month = $start->copy()->addMonthsNoOverflow($i);
            $series[] = ['label' => Str::ucfirst($month->translatedFormat('M')), 'value' => $sums->get($month->format('Y-m'), 0.0)];
        }

        return $series;
    }

    /**
     * Lo más seguido: cuenta cuántos suscriptores piden cada valor (ignora mayúsculas).
     *
     * @param  array<int, string>  $fields
     * @return array<int, array{label: string, value: int}>
     */
    private static function top(Collection $subscribers, array $fields, int $limit, callable $label): array
    {
        $counts = [];
        foreach ($subscribers as $subscriber) {
            $values = collect($fields)->flatMap(fn (string $f) => $subscriber->{$f} ?? [])->map(fn ($v) => trim((string) $v))->filter()->unique(fn ($v) => Str::lower($v));
            foreach ($values as $value) {
                $key = Str::lower($value);
                $counts[$key] = ['label' => $label($value), 'value' => ($counts[$key]['value'] ?? 0) + 1];
            }
        }

        return collect($counts)->sortByDesc('value')->take($limit)->values()->all();
    }
}
