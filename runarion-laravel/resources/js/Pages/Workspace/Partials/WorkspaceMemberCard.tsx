import { Checkbox } from "@/Components/ui/checkbox";
import { WorkspaceMember } from "@/types/workspace";

export default function WorkspaceMemberCard({
    member,
    isSelf,
    isUserOwner,
    isUserAdmin,
    checked = false,
    onCheckedChange = () => {},
}: {
    member: WorkspaceMember;
    isSelf: boolean;
    isUserOwner: boolean;
    isUserAdmin: boolean;
    checked?: boolean;
    onCheckedChange?: (checked: boolean) => void;
}) {
    const showCheckbox =
        !isSelf &&
        ((member.role === "member" && (isUserOwner || isUserAdmin)) ||
            (member.role === "admin" && isUserOwner));
    const containerWidth = 14;
    const checkboxWidth = 1;

    return (
        <div
            className={
                "flex items-center justify-between px-2 py-1 bg-gray-200 rounded"
            }
            style={{
                width: `${containerWidth}rem`,
            }}
        >
            <div
                className={"flex flex-col"}
                style={{
                    width: showCheckbox
                        ? `${containerWidth - checkboxWidth - 1.5}rem`
                        : "100%",
                }}
            >
                <div
                    className="overflow-hidden text-ellipsis whitespace-nowrap text-sm"
                    style={member.name ? {} : { fontStyle: "italic" }}
                >
                    {member.name || "Invited"}
                </div>
                <div className="flex items-center gap-1 text-gray-600 text-xs">
                    <div className="overflow-hidden text-ellipsis whitespace-nowrap">
                        {member.email}
                    </div>
                    {member.is_verified === false && (
                        <div>{"(unverified)"}</div>
                    )}
                </div>
            </div>
            <div
                className={"flex items-center justify-center"}
                style={{
                    width: `${checkboxWidth}rem`,
                }}
            >
                {showCheckbox && (
                    <Checkbox
                        checked={checked}
                        onCheckedChange={onCheckedChange}
                        className="bg-white"
                    />
                )}
            </div>
        </div>
    );
}
