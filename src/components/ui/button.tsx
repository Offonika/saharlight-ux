import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium ring-offset-background transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-gradient-button text-primary-foreground shadow-soft hover:shadow-medium hover:scale-[1.02] active:scale-[0.98] disabled:shadow-none",
        destructive:
          "bg-gradient-to-r from-destructive to-red-600 text-destructive-foreground shadow-soft hover:shadow-medium hover:scale-[1.02]",
        outline:
          "border border-medical-blue/30 bg-background/60 backdrop-blur-sm hover:bg-medical-blue/10 hover:text-medical-blue hover:border-medical-blue/60",
        secondary:
          "bg-gradient-to-r from-secondary to-secondary/80 text-secondary-foreground shadow-soft hover:shadow-medium hover:scale-[1.02] active:scale-[0.98]",
        ghost: "hover:bg-accent/80 hover:text-accent-foreground transition-all duration-200",
        link: "text-medical-blue underline-offset-4 hover:underline hover:text-medical-blue-light",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-12 rounded-xl px-6 py-3 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, type, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        type={asChild ? type : type ?? "button"}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
