<?php

namespace App\Services;

use App\Models\AuthorStyle;
use Illuminate\Support\Collection;

class AuthorStyleFormatter
{
    public function format(AuthorStyle $style, bool $includeDetails = false): array
    {
        $colors = ['bg-blue-100', 'bg-emerald-100', 'bg-amber-100', 'bg-rose-100', 'bg-cyan-100', 'bg-orange-100'];
        $colorIndex = crc32($style->id) % count($colors);

        $result = [
            'id' => $style->id,
            'name' => $style->author_name,
            'author_name' => $style->author_name,
            'fileCount' => 1,
            'avatar' => strtoupper(substr($style->author_name, 0, 1)),
            'color' => $colors[$colorIndex],
            'status' => $style->status ?? 'init_completed',
            'schemaVersion' => (int) ($style->schema_version ?? 1),
            'projectIds' => array_values(array_filter([$style->project_id])),
        ];

        if ($includeDetails || $style->status === 'profiling_completed') {
            $result['techniques'] = $style->techniques_json ?? (object) [];
            $result['examples'] = $style->examples_json ?? (object) [];
            $result['adaptation'] = $style->adaptation_json ?? (object) [];
        }

        return $result;
    }

    public function formatCollection(Collection $styles, bool $includeDetails = false): array
    {
        return $styles
            ->map(fn (AuthorStyle $style) => $this->format($style, $includeDetails))
            ->values()
            ->all();
    }
}
