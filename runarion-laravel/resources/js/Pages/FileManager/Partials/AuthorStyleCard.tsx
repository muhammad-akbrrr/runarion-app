import React from "react";
import { AuthorStyle } from "@/types/files";
import { Button } from "@/Components/ui/button";
import { CirclePlus } from "lucide-react";

interface AuthorStyleCardProps {
  authorStyles: AuthorStyle[];
  onAddClick: () => void;
}

export default function AuthorStyleCard({ authorStyles, onAddClick }: AuthorStyleCardProps) {
  return (
    <div className="space-y-4">
        <div className="flex justify-between items-center">
            <h2 className="text-xl">Author Styles</h2>
            <Button
              variant="default"
              onClick={onAddClick}
            >
                <CirclePlus className="h-4 w-4" />
                Add Author Style
            </Button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            {authorStyles.length > 0 ? (
                authorStyles.map((style) => (
                    <div
                        key={style.id}
                        className="w-full bg-white rounded-md border"
                    >
                        <div className="p-4 relative flex flex-col items-stretch justofy-between gap-3">
                            <div className="flex flex-row items-start justify-between gap-3">
                                <div
                                    className={`${style.color} p-2 rounded-full flex items-center justify-center font-medium`}
                                >
                                    <div className="w-4 h-4">
                                        {style.avatar}
                                    </div>
                                </div>
                                <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">
                                    {style.fileCount} Files
                                </span>
                            </div>
                            <div className="truncate">
                                <p className="font-medium text-sm">
                                    {style.name}
                                </p>
                            </div>
                        </div>
                    </div>
                ))
            ) : (
                <div className="w-full col-span-4 text-center py-8 text-muted-foreground">
                    You don't have any author styles yet.
                </div>
            )}
        </div>
    </div>
  );
}
