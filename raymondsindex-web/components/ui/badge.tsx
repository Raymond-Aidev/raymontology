import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  // Linear-style badge base
  "inline-flex items-center justify-center rounded-md border px-2 py-0.5 text-xs font-medium w-fit whitespace-nowrap shrink-0 [&>svg]:size-3 gap-1 [&>svg]:pointer-events-none transition-colors overflow-hidden",
  {
    variants: {
      variant: {
        // Primary: Dark on light
        default:
          "border-transparent bg-gray-900 text-white",
        // Secondary: Light surface
        secondary:
          "border-gray-200 bg-gray-100 text-gray-700",
        // Destructive: Red
        destructive:
          "border-transparent bg-red-600/20 text-red-400",
        // Outline: Transparent with border
        outline:
          "border-gray-300 bg-transparent text-gray-600",
        // Success: Green
        success:
          "border-transparent bg-green-600/20 text-green-400",
        // Warning: Yellow/Orange
        warning:
          "border-transparent bg-yellow-600/20 text-yellow-400",
        // Accent: Linear purple
        accent:
          "border-transparent bg-[#5E6AD2]/20 text-[#8B95E8]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({
  className,
  variant,
  asChild = false,
  ...props
}: React.ComponentProps<"span"> &
  VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "span"

  return (
    <Comp
      data-slot="badge"
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
