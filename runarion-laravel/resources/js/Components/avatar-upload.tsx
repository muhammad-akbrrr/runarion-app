import { Avatar, AvatarFallback, AvatarImage } from "@/Components/ui/avatar";
import { Button } from "@/Components/ui/button";
import { Label } from "@/Components/ui/label";
import { LucideProps } from "lucide-react";
import { createElement, useRef, useState } from "react";

function AvatarUpload({
    label,
    src,
    onChange,
    fallback,
    error,
    className,
}: {
    label: string;
    src: string | null;
    onChange: (file: File) => void;
    fallback?:
        | string
        | React.ForwardRefExoticComponent<
              Omit<LucideProps, "ref"> & React.RefAttributes<SVGSVGElement>
          >;
    error?: string;
    className?: string;
}) {
    const fileInputRef = useRef<HTMLInputElement>(null);

    const [previewUrl, setPreviewUrl] = useState<string | null>(src);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            onChange(file);
            setPreviewUrl(URL.createObjectURL(file));
        }
    };

    return (
        <div className={`flex flex-row items-center ${className}`}>
            <Label className="w-full" htmlFor="avatar_upload">
                {label}
            </Label>
            <div className="flex flex-row items-center gap-4 w-full">
                <Avatar className="w-16 h-16">
                    <AvatarImage
                        src={previewUrl ?? undefined}
                        alt={label}
                        className="object-cover object-center"
                    />
                    <AvatarFallback>
                        {typeof fallback === "string" || fallback === undefined
                            ? fallback ?? ""
                            : createElement(fallback, {
                                  className: "w-8 h-8",
                              })}
                    </AvatarFallback>
                </Avatar>
                <div>
                    <Button
                        type="button"
                        variant="secondary"
                        onClick={() => fileInputRef.current?.click()}
                    >
                        {src ? "Change" : "Upload"} Photo
                    </Button>
                    <input
                        type="file"
                        accept="image/*"
                        className="hidden"
                        ref={fileInputRef}
                        onChange={handleFileChange}
                    />
                </div>
                {error && (
                    <div className="text-sm text-destructive max-w-70">
                        {error}
                    </div>
                )}
            </div>
        </div>
    );
}

export { AvatarUpload };
