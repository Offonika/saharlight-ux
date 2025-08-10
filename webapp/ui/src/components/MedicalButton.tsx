import React from 'react';
import { Button, type ButtonProps } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export interface MedicalButtonProps extends Omit<ButtonProps, 'variant'> {
  variant?: 'primary' | 'secondary' | 'icon';
}

const MedicalButton = React.forwardRef<HTMLButtonElement, MedicalButtonProps>(
  ({ variant = 'primary', className, size, ...props }, ref) => {
    const buttonVariant = variant === 'secondary' ? 'secondary' : 'default';
    const buttonSize = variant === 'icon' ? 'icon' : size ?? 'lg';

    return (
      <Button
        ref={ref}
        variant={buttonVariant}
        size={buttonSize}
        className={cn(variant === 'icon' && 'rounded-lg', className)}
        {...props}
      />
    );
  }
);

MedicalButton.displayName = 'MedicalButton';

export { MedicalButton };
export default MedicalButton;
