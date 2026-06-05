<?php

namespace App\Services;

use Illuminate\Http\Client\PendingRequest;
use Illuminate\Http\Client\Response;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Http;
use RuntimeException;

class PythonServiceClient
{
    public function baseUrl(): string
    {
        return rtrim((string) config('services.python.url', 'http://python-app:5000'), '/');
    }

    public function get(string $path, array $query = []): array
    {
        $response = $this->request()
            ->acceptJson()
            ->get($this->url($path), $query);

        return $this->decodeResponse($response);
    }

    public function postMultipart(string $path, array $multipart): array
    {
        $response = $this->request()
            ->asMultipart()
            ->post($this->url($path), $multipart);

        return $this->decodeResponse($response);
    }

    public function startNovelPipeline(array $payload, UploadedFile $manuscriptFile, array $authorFiles = []): array
    {
        $parts = [];
        $handles = [];

        try {
            $manuscriptHandle = fopen($manuscriptFile->getRealPath(), 'rb');
            if ($manuscriptHandle === false) {
                throw new RuntimeException('Failed to open manuscript upload');
            }

            $handles[] = $manuscriptHandle;
            $parts[] = [
                'name' => 'manuscript_file',
                'contents' => $manuscriptHandle,
                'filename' => $manuscriptFile->getClientOriginalName(),
            ];

            foreach ($authorFiles as $authorFile) {
                if (! $authorFile instanceof UploadedFile) {
                    continue;
                }

                $handle = fopen($authorFile->getRealPath(), 'rb');
                if ($handle === false) {
                    throw new RuntimeException(sprintf(
                        'Failed to open author sample upload: %s',
                        $authorFile->getClientOriginalName()
                    ));
                }

                $handles[] = $handle;
                $parts[] = [
                    'name' => 'author_files',
                    'contents' => $handle,
                    'filename' => $authorFile->getClientOriginalName(),
                ];
            }

            $parts[] = [
                'name' => 'data',
                'contents' => json_encode($payload, JSON_THROW_ON_ERROR),
            ];

            return $this->postMultipart('/api/novel-pipeline/start', $parts);
        } finally {
            foreach ($handles as $handle) {
                if (is_resource($handle)) {
                    fclose($handle);
                }
            }
        }
    }

    public function getNovelPipelineStatus(string $runId, int $userId): array
    {
        return $this->get(sprintf('/api/novel-pipeline/status/%s', $runId), [
            'user_id' => $userId,
        ]);
    }

    public function getNovelPipelineResults(string $runId, int $userId): array
    {
        return $this->get(sprintf('/api/novel-pipeline/results/%s', $runId), [
            'user_id' => $userId,
        ]);
    }

    public function analyzeAuthorStyle(array $payload, array $filePaths): array
    {
        $parts = [];
        $handles = [];

        try {
            foreach ($filePaths as $filePath) {
                $handle = fopen($filePath, 'rb');
                if ($handle === false) {
                    throw new RuntimeException(sprintf('Failed to open author style file: %s', $filePath));
                }

                $handles[] = $handle;
                $parts[] = [
                    'name' => 'files',
                    'contents' => $handle,
                    'filename' => basename($filePath),
                ];
            }

            $parts[] = [
                'name' => 'data',
                'contents' => json_encode($payload, JSON_THROW_ON_ERROR),
            ];

            return $this->postMultipart('/api/analyze-style', $parts);
        } finally {
            foreach ($handles as $handle) {
                if (is_resource($handle)) {
                    fclose($handle);
                }
            }
        }
    }

    private function request(): PendingRequest
    {
        return Http::timeout(900)
            ->withoutVerifying()
            ->acceptJson();
    }

    private function url(string $path): string
    {
        return $this->baseUrl().'/'.ltrim($path, '/');
    }

    private function decodeResponse(Response $response): array
    {
        $decoded = $response->json();

        if (! $response->successful()) {
            throw new RuntimeException($this->extractErrorMessage($decoded, $response));
        }

        if (! is_array($decoded)) {
            throw new RuntimeException('Python service returned an invalid response payload.');
        }

        if (($decoded['success'] ?? true) === false) {
            throw new RuntimeException($this->extractErrorMessage($decoded, $response));
        }

        return $decoded['data'] ?? $decoded;
    }

    private function extractErrorMessage(mixed $decoded, Response $response): string
    {
        if (is_array($decoded)) {
            if (! empty($decoded['error'])) {
                return (string) $decoded['error'];
            }

            $fieldErrors = $decoded['details']['field_errors'] ?? null;
            if (is_array($fieldErrors)) {
                foreach ($fieldErrors as $messages) {
                    if (is_array($messages) && ! empty($messages[0])) {
                        return (string) $messages[0];
                    }
                }
            }
        }

        return sprintf(
            'Python service request failed with status %d.',
            $response->status()
        );
    }
}
