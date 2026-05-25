import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-sm border px-2 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default:     "border-transparent bg-primary/20 text-primary",
        secondary:   "border-transparent bg-secondary text-secondary-foreground",
        destructive: "border-transparent bg-destructive/20 text-destructive",
        outline:     "border-border text-foreground",
        win:         "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
        loss:        "border-red-500/30 bg-red-500/10 text-red-400",
        blue:        "border-blue-500/30 bg-blue-500/10 text-blue-400",
        red:         "border-red-500/30 bg-red-500/10 text-red-400",
        fight:       "border-orange-500/30 bg-orange-500/10 text-orange-400",
        objective:   "border-violet-500/30 bg-violet-500/10 text-violet-400",
        lane:        "border-cyan-500/30 bg-cyan-500/10 text-cyan-400",
        jungle:      "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
        recall:      "border-zinc-500/30 bg-zinc-500/10 text-zinc-400",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
