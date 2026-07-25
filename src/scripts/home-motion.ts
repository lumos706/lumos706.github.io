import { waapi, type WAAPIAnimation } from 'animejs/waapi';
import { stagger } from 'animejs/utils';

const PENDING_CLASS = 'home-motion-pending';
const ACTIVE_CLASS = 'home-motion-active';
const EASE_OUT = 'cubic-bezier(0.22, 1, 0.36, 1)';
const MOTION_SELECTOR = '[data-home-motion]';
const REVEAL_SELECTOR = '[data-home-motion="reveal"]';

export function initHomeMotion() {
  const root = document.documentElement;
  const motionPreference = matchMedia('(prefers-reduced-motion: reduce)');
  const motionElements = Array.from(document.querySelectorAll<HTMLElement>(MOTION_SELECTOR));

  const revealEverything = () => {
    root.classList.remove(PENDING_CLASS, ACTIVE_CLASS);
    motionElements.forEach((element) => element.removeAttribute('data-home-motion-state'));
  };

  if (
    motionPreference.matches
    || !root.classList.contains(PENDING_CLASS)
    || !('animate' in Element.prototype)
    || motionElements.length === 0
  ) {
    revealEverything();
    return;
  }

  const runningAnimations = new Set<WAAPIAnimation>();
  let observer: IntersectionObserver | undefined;

  const track = (animation: WAAPIAnimation) => {
    runningAnimations.add(animation);
    return animation;
  };

  const finishRunningAnimations = () => {
    runningAnimations.forEach((animation) => animation.complete());
  };

  const removeInteractionListeners = () => {
    document.removeEventListener('pointerdown', finishRunningAnimations);
    document.removeEventListener('keydown', finishRunningAnimations);
    window.removeEventListener('wheel', finishRunningAnimations);
  };

  const disableMotion = () => {
    observer?.disconnect();
    runningAnimations.forEach((animation) => animation.revert());
    runningAnimations.clear();
    removeInteractionListeners();
    revealEverything();
  };

  try {
    root.classList.add(ACTIVE_CLASS);

    const introItems = Array.from(document.querySelectorAll<HTMLElement>('[data-home-motion="intro"]'));
    if (introItems.length) {
      let introAnimation: WAAPIAnimation;
      introAnimation = track(waapi.animate(introItems, {
        opacity: { from: 0, to: 1 },
        y: { from: 18, to: 0 },
        duration: 540,
        delay: stagger(85, { start: 40 }),
        ease: EASE_OUT,
        onComplete: () => runningAnimations.delete(introAnimation),
      }));
    }

    const heroVisual = document.querySelector<HTMLElement>('[data-home-motion="intro-visual"]');
    if (heroVisual) {
      let visualAnimation: WAAPIAnimation;
      visualAnimation = track(waapi.animate(heroVisual, {
        opacity: { from: 0, to: 1 },
        y: { from: 24, to: 0 },
        scale: { from: 0.985, to: 1 },
        duration: 680,
        delay: 150,
        ease: EASE_OUT,
        onComplete: () => runningAnimations.delete(visualAnimation),
      }));
    }

    const playGroup = (group: HTMLElement) => {
      try {
        const targets = Array.from(group.querySelectorAll<HTMLElement>(REVEAL_SELECTOR))
          .filter((element) => element.dataset.homeMotionState !== 'played');

        if (!targets.length) return;

        let groupAnimation: WAAPIAnimation;
        groupAnimation = track(waapi.animate(targets, {
          opacity: { from: 0, to: 1 },
          y: { from: 18, to: 0 },
          duration: 480,
          delay: stagger(65),
          ease: EASE_OUT,
          onComplete: () => {
            targets.forEach((element) => { element.dataset.homeMotionState = 'played'; });
            runningAnimations.delete(groupAnimation);
            if (!document.querySelector(`${REVEAL_SELECTOR}:not([data-home-motion-state="played"])`)) {
              root.classList.remove(ACTIVE_CLASS);
            }
          },
        }));
      } catch {
        disableMotion();
      }
    };

    const groups = Array.from(document.querySelectorAll<HTMLElement>('[data-home-motion-group]'));
    if ('IntersectionObserver' in window) {
      observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          playGroup(entry.target as HTMLElement);
          observer?.unobserve(entry.target);
        });
      }, { rootMargin: '0px 0px -8% 0px', threshold: 0.12 });
      groups.forEach((group) => observer?.observe(group));
    } else {
      document.querySelectorAll<HTMLElement>(REVEAL_SELECTOR).forEach((element) => {
        element.dataset.homeMotionState = 'played';
      });
      root.classList.remove(ACTIVE_CLASS);
    }

    root.classList.remove(PENDING_CLASS);

    document.addEventListener('pointerdown', finishRunningAnimations, { passive: true });
    document.addEventListener('keydown', finishRunningAnimations);
    window.addEventListener('wheel', finishRunningAnimations, { passive: true });

    const handleMotionPreference = (event: MediaQueryListEvent) => {
      if (event.matches) disableMotion();
    };
    motionPreference.addEventListener('change', handleMotionPreference, { once: true });

    window.addEventListener('pagehide', () => {
      finishRunningAnimations();
      observer?.disconnect();
      removeInteractionListeners();
      root.classList.remove(PENDING_CLASS, ACTIVE_CLASS);
      motionPreference.removeEventListener('change', handleMotionPreference);
    }, { once: true });
  } catch {
    disableMotion();
  }
}
