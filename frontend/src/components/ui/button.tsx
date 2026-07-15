import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex cursor-pointer items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-[color,background-color,border-color,box-shadow] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground shadow-panel hover:bg-primary/90",
        success:
          "bg-success text-success-foreground shadow-panel hover:bg-success/90",
        destructive:
          "bg-destructive text-destructive-foreground shadow-panel hover:bg-destructive/90",
        warning:
          "bg-warning text-warning-foreground shadow-panel hover:bg-warning/90",
        outline:
          "border border-input bg-card text-foreground shadow-panel hover:border-primary/30 hover:bg-accent hover:text-accent-foreground",
        successOutline:
          "border border-success/25 bg-card text-success hover:bg-success/10",
        destructiveOutline:
          "border border-destructive/25 bg-card text-destructive hover:bg-destructive/10",
        warningOutline:
          "border border-warning/25 bg-card text-warning hover:bg-warning/10",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-secondary/75",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4",
        xs: "h-7 rounded-md px-2.5 text-xs",
        sm: "h-8 rounded-md px-3 text-sm",
        lg: "h-10 rounded-md px-6",
        icon: "h-9 w-9",
        iconSm: "h-8 w-8",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
