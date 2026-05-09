<?php

namespace App\Services;

class LexicalContentSerializer
{
    public function plainTextToOriginLexical(string $text, string $origin = 'ai'): string
    {
        $normalized = str_replace(["\r\n", "\r"], "\n", $text);
        $lines = explode("\n", $normalized);
        $children = [];

        if (empty($lines)) {
            $lines = [''];
        }

        foreach ($lines as $line) {
            $paragraphChildren = [];
            if ($line === '') {
                $paragraphChildren[] = $this->originTextNode("\n", $origin);
            } else {
                $paragraphChildren[] = $this->originTextNode($line, $origin);
            }

            $children[] = [
                'type' => 'paragraph',
                'version' => 1,
                'format' => '',
                'indent' => 0,
                'direction' => null,
                'textFormat' => 0,
                'textStyle' => '',
                'children' => $paragraphChildren,
            ];
        }

        return json_encode([
            'root' => [
                'type' => 'root',
                'version' => 1,
                'format' => '',
                'indent' => 0,
                'direction' => null,
                'children' => $children,
            ],
        ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR);
    }

    private function originTextNode(string $text, string $origin): array
    {
        return [
            'type' => 'origin-text',
            'version' => 1,
            'text' => $text,
            'origin' => $origin,
            'detail' => 0,
            'format' => 0,
            'mode' => 'normal',
            'style' => '',
        ];
    }
}
