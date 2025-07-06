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
          <CirclePlus className="mr-2 h-4 w-4" />
          Add Author Style
        </Button>
      </div>
      <div className="flex space-x-4 overflow-auto pb-2">
        {authorStyles.length > 0 ? (
          authorStyles.map((style) => (
            <div key={style.id} className="min-w-[250px] max-w-[300px] bg-white rounded-lg border">
              <div className="p-4 relative">
                <span className="absolute top-2 right-2 text-xs bg-gray-100 px-2 py-0.5 rounded">
                  {style.fileCount} Files
                </span>
                <div className="flex items-center gap-3 mt-4">
                  <div className={`${style.color} w-10 h-10 rounded-full flex items-center justify-center font-medium`}>
                    {style.avatar}
                  </div>
                  <div className="truncate">
                    <h3 className="font-medium text-sm">{style.name}</h3>
                  </div>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="w-full text-center py-8 text-muted-foreground">
            No author styles found. Create one by clicking the "Add Author Style" button.
          </div>
        )}
      </div>
    </div>
  );
}
