import React from "react";
import { StorageProvider } from "@/types/files";
import { Cloud, Folder, HardDrive } from "lucide-react";

interface StorageCardsProps {
  storageProviders: StorageProvider[];
}

export default function StorageCards({ storageProviders }: StorageCardsProps) {
  // Sort storage providers: enabled first (with Local Storage at the beginning), then disabled
  const sortedStorageProviders = [...storageProviders].sort((a, b) => {
    // Local Storage is always first
    if (a.name === "Local Storage") return -1;
    if (b.name === "Local Storage") return 1;
    
    // Then sort by enabled status
    if (a.enabled && !b.enabled) return -1;
    if (!a.enabled && b.enabled) return 1;
    
    // If both have the same enabled status, keep original order
    return 0;
  });

  // Function to get the appropriate icon component based on the icon name
  const getIconComponent = (iconName: string) => {
    switch (iconName) {
      case 'Cloud':
        return Cloud;
      case 'Dropbox':
        return Cloud;
      case 'HardDrive':
        return HardDrive;
      default:
        return Folder;
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl">File Manager</h2>
      </div>
      
      {/* Storage Cards - 4 column grid on md+, 2 column on sm, 1 column on xs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          {sortedStorageProviders.map((provider) => {
              const IconComponent = getIconComponent(
                  provider.icon
              );
              return (
                  <div
                      key={provider.id}
                      className={`bg-white rounded-md border ${
                          !provider.enabled ? "opacity-60" : ""
                      }`}
                  >
                      <div className="p-4">
                          <div className="flex items-center gap-3">
                              <div
                                  className={`${provider.color} p-2 rounded-full bg-gray-100`}
                              >
                                  <IconComponent className="h-4 w-4" />
                              </div>
                              <div className="flex-1">
                                  <h3 className="font-medium">
                                      {provider.name}
                                  </h3>
                              </div>
                          </div>

                          {provider.enabled && (
                              <div className="mt-3 space-y-2">
                                  <div className="h-1 w-full bg-gray-200 rounded">
                                      <div
                                          className="h-1 rounded bg-gray-700"
                                          style={{
                                              width: `${provider.percentage}%`,
                                          }}
                                      />
                                  </div>
                                  <div className="text-sm text-muted-foreground">
                                      {provider.used}GB /{" "}
                                      {provider.total}GB
                                  </div>
                              </div>
                          )}

                          {!provider.enabled && (
                              <div className="mt-3 space-y-2">
                                  <div className="h-1 w-full bg-gray-200 rounded"></div>
                                  <div className="text-sm text-muted-foreground">
                                      ∞ / ∞
                                  </div>
                              </div>
                          )}
                      </div>
                  </div>
              );
          })}
      </div>
    </div>
  );
}
