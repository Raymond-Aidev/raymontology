import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  // Linear-style base button
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:ring-2 focus-visible:ring-[#5E6AD2]/50 focus-visible:ring-offset-2 focus-visible:ring-offset-white",
  {
    variants: {
      variant: {
        // Primary button
        default: "bg-gray-900 text-white hover:bg-gray-800 active:bg-gray-700",
        // Destructive: Red
        destructive:
          "bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-500/50",
        // Outline: Transparent with border
        outline:
          "border border-gray-300 bg-transparent text-gray-700 hover:bg-gray-50 hover:text-gray-900 hover:border-gray-400",
        // Secondary: Light surface
        secondary:
          "bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-200",
        // Ghost: Minimal, no border
        ghost:
          "text-gray-500 hover:text-gray-900 hover:bg-gray-100",
        // Link: Underlined text
        link: "text-gray-600 underline-offset-4 hover:underline hover:text-gray-900",
        // Accent: Linear purple
        accent:
          "bg-[#5E6AD2] text-white hover:bg-[#7C85E0] focus-visible:ring-[#5E6AD2]/50",
      },
      size: {
        default: "h-9 px-4 py-2 has-[>svg]:px-3",
        sm: "h-7 rounded-md gap-1.5 px-3 text-xs has-[>svg]:px-2",
        lg: "h-11 rounded-lg px-6 has-[>svg]:px-4",
        icon: "size-9",
        "icon-sm": "size-7",
        "icon-lg": "size-11",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
